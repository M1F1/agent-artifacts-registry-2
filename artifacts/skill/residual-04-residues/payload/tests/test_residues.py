"""Tests for step 04: mirrored ids, the looping measurement, sibling context.

    python skills/residual-04-residues/scripts/run.py test
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from residual import fs, merge, profiles, prompt, registry, run, validate
from residual.config import Config
from residual.model import Unit

STEP = "04-residues"


class ResidueStepTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".residuality"
        self.spec = registry.spec(STEP)
        self.config = Config(root=self.root)
        self.profile = profiles.Profile()
        self.ctx = run.create(run.RunContext(root=self.root, slug="d", mode="loop"))

        fs.write_csv(
            self.ctx.dir / "03-stressors/register.csv",
            ("id", "lens", "stressor", "detection", "attractor", "business_reaction"),
            [
                {"id": f"S{i:04d}", "lens": "l", "stressor": f"s{i}", "detection": "d", "attractor": "a", "business_reaction": "b"}
                for i in (1, 2)
            ],
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, records, shard="b001"):
        fs.write_jsonl(run.shard_path(self.ctx, self.spec, shard), records)
        merge.run(self.ctx, self.spec)
        return validate.run(self.ctx, self.spec, self.config, self.profile)

    def test_residue_ids_mirror_their_stressor(self):
        self._run(
            [
                {"stressor_id": "S0001", "change": "pin the price at order time", "components": ["PriceStore"]},
                {"stressor_id": "S0002", "change": "buffer the sends", "components": ["Outbox"]},
            ]
        )
        self.assertEqual([r.id for r in merge.load_residues(self.ctx)], ["R0001", "R0002"])

    def test_looping_is_counted_not_penalised(self):
        gate = self._run(
            [
                {"stressor_id": "S0001", "change": "pin the price at order time", "components": ["PriceStore"]},
                {"stressor_id": "S0002", "change": "", "already_survived_by": ["R0001"]},
            ]
        )
        self.assertEqual(gate.stats["looping"], 1)
        self.assertAlmostEqual(gate.stats["looping_rate"], 0.5)
        self.assertNotIn("empty-residue", {i.code for i in gate.errors})

    def test_a_loop_pointing_nowhere_is_an_error(self):
        gate = self._run(
            [
                {"stressor_id": "S0001", "change": "pin the price", "components": ["PriceStore"]},
                {"stressor_id": "S0002", "change": "", "already_survived_by": ["R9999"]},
            ]
        )
        self.assertIn("dangling-loop", {i.code for i in gate.errors})

    def test_a_stressor_with_no_residue_is_reported(self):
        gate = self._run([{"stressor_id": "S0001", "change": "pin the price", "components": ["PriceStore"]}])
        self.assertEqual(
            {i.where for i in gate.errors if i.code == "stressor-unaddressed"}, {"S0002"}
        )

    def test_a_residue_with_neither_change_nor_loop_is_empty(self):
        gate = self._run(
            [
                {"stressor_id": "S0001", "change": "", "rationale": "thinking about it"},
                {"stressor_id": "S0002", "change": "buffer the sends", "components": ["Outbox"]},
            ]
        )
        self.assertIn("empty-residue", {i.code for i in gate.errors})


class ResiduePromptTests(unittest.TestCase):
    """This is the one step whose prompt hands the agent its siblings' work."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".residuality"
        self.spec = registry.spec(STEP)
        self.config = Config(root=self.root)
        self.profile = profiles.Profile()
        self.ctx = run.create(run.RunContext(root=self.root, slug="dp", mode="loop"))

    def tearDown(self):
        self._tmp.cleanup()

    def _render(self) -> str:
        unit = Unit(
            id=f"{STEP}--b002",
            step=STEP,
            shard="b002",
            payload={"ids": ["S0002"], "rows": [{"id": "S0002", "stressor": "a supplier exits the market"}]},
        )
        return prompt.render(unit, self.spec, self.ctx, self.config, self.profile)

    def test_prompt_requires_reading_siblings(self):
        text = self._render()
        self.assertIn("you **should** look at what the other", text)
        self.assertNotIn("Do **not** read anything else", text)

    def test_earlier_residues_are_summarised_in_the_prompt(self):
        fs.write_jsonl(
            run.shard_path(self.ctx, self.spec, "b001"),
            [{"stressor_id": "S0001", "change": "pin the price at order time", "components": ["PriceStore"]}],
        )
        text = self._render()
        self.assertIn("pin the price at order time", text)
        self.assertIn("R0001", text)

    def test_the_first_unit_is_told_it_is_first(self):
        self.assertIn("yours is the first", self._render())


if __name__ == "__main__":
    unittest.main()
