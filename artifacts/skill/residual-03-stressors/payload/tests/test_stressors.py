"""Tests for step 03: identifiers, the gate, the report and the sibling ban.

    python skills/residual-03-stressors/scripts/run.py test
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from residual import fs, merge, profiles, prompt, registry, run, validate
from residual.config import Config
from residual.model import Unit

STEP = "03-stressors"
GROUNDED = {
    "stressor": "The tariff table gains a night band that session ingest misreads as the day rate",
    "detection": "revenue drifts from meter readings",
    "attractor": "finance rebuilds revenue by hand",
    "business_reaction": "freeze tariff changes behind review",
}


class StressorCompileTests(unittest.TestCase):
    """Identifiers must not depend on which execution mode produced the shards."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".residuality"
        self.spec = registry.spec(STEP)

    def tearDown(self):
        self._tmp.cleanup()

    def _seed(self, slug: str, shard_order: tuple[str, ...]) -> run.RunContext:
        ctx = run.create(run.RunContext(root=self.root, slug=slug, mode="loop"))
        rows = {
            "alpha": [{"stressor": "a1", "detection": "d", "attractor": "at", "business_reaction": "b"}],
            "beta": [{"stressor": "b1", "detection": "d", "attractor": "at", "business_reaction": "b"}],
        }
        for shard in shard_order:
            fs.write_jsonl(run.shard_path(ctx, self.spec, shard), rows[shard])
        return ctx

    def test_ids_are_independent_of_write_order(self):
        first = merge.run(self._seed("one", ("alpha", "beta")), self.spec)
        second = merge.run(self._seed("two", ("beta", "alpha")), self.spec)
        self.assertEqual(
            fs.read_text(first.outputs[0]),
            fs.read_text(second.outputs[0]),
            "compiled register differs by shard write order",
        )

    def test_register_ids_carry_the_training_prefix(self):
        ctx = self._seed("three", ("alpha",))
        merge.run(ctx, self.spec)
        stressors = merge.load_stressors(ctx, self.spec)
        self.assertEqual(stressors[0].id, "S0001")

    def test_lens_defaults_to_the_shard_name(self):
        ctx = self._seed("four", ("alpha",))
        merge.run(ctx, self.spec)
        self.assertEqual(merge.load_stressors(ctx, self.spec)[0].lens, "alpha")


class StressorGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".residuality"
        self.spec = registry.spec(STEP)
        self.config = Config(root=self.root)
        self.profile = profiles.Profile(vocabulary=("tariff table", "session ingest"))
        self.ctx = run.create(run.RunContext(root=self.root, slug="g", mode="loop"))

    def tearDown(self):
        self._tmp.cleanup()

    def _gate(self, records):
        fs.write_jsonl(run.shard_path(self.ctx, self.spec, "lens"), records)
        merge.run(self.ctx, self.spec)
        return validate.run(self.ctx, self.spec, self.config, self.profile)

    def test_generic_stressor_fails(self):
        result = self._gate(
            [{"stressor": "The server goes down", "detection": "alert", "attractor": "outage", "business_reaction": "restore"}]
        )
        self.assertIn("generic-stressor", {i.code for i in result.errors})

    def test_grounded_stressor_passes_specificity(self):
        result = self._gate([GROUNDED])
        self.assertNotIn("generic-stressor", {i.code for i in result.errors})

    def test_banned_field_is_an_error(self):
        result = self._gate([{**GROUNDED, "probability": 0.4}])
        self.assertIn("banned-field", {i.code for i in result.errors})

    def test_empty_register_fails(self):
        self.assertFalse(self._gate([]).ok)


class StressorReportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".residuality"
        self.spec = registry.spec(STEP)
        self.ctx = run.create(run.RunContext(root=self.root, slug="r", mode="loop"))
        self.config = Config(root=self.root)
        self.profile = profiles.Profile(vocabulary=("tariff table",))
        self._write([{**GROUNDED, "stressor": "tariff table drift"}])

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, records):
        fs.write_jsonl(run.shard_path(self.ctx, self.spec, "lens"), records)
        merge.run(self.ctx, self.spec)

    def _render(self) -> str:
        gate = validate.run(self.ctx, self.spec, self.config, self.profile)
        return registry.call(STEP, "report", self.ctx, self.spec, gate, self.profile)

    def test_report_is_byte_identical_across_renders(self):
        self.assertEqual(self._render(), self._render())

    def test_report_is_self_contained_and_theme_aware(self):
        html = self._render()
        # The SVG xmlns is a namespace identifier, not a fetch, so look for the
        # constructs that would actually pull a resource over the network.
        for external in ("src=", "href=", "@import", "url(http", "fetch("):
            self.assertNotIn(external, html, f"report loads something external via {external}")
        self.assertIn("prefers-color-scheme", html)
        self.assertIn('data-theme="dark"', html)

    def test_cell_content_is_escaped(self):
        self._write([{**GROUNDED, "stressor": "<script>alert(1)</script>"}])
        self.assertNotIn("<script>alert(1)</script>", self._render())


class StressorPromptTests(unittest.TestCase):
    """Blind generation is the whole method; the prompt has to say so."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".residuality"
        self.ctx = run.create(run.RunContext(root=self.root, slug="p", mode="loop"))
        self.config = Config(root=self.root)
        self.profile = profiles.Profile()

    def tearDown(self):
        self._tmp.cleanup()

    def _render(self) -> str:
        unit = Unit(
            id=f"{STEP}--x", step=STEP, shard="x", payload={"lens": "x", "provoke": "what if"}
        )
        return prompt.render(unit, registry.spec(STEP), self.ctx, self.config, self.profile)

    def test_prompt_forbids_reading_siblings(self):
        self.assertIn("Do **not** read anything else", self._render())

    def test_prompt_bans_the_scoring_fields(self):
        text = self._render()
        for banned in ("probability", "impact", "cost", "priority"):
            self.assertIn(banned, text)


if __name__ == "__main__":
    unittest.main()
