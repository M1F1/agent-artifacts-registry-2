"""Tests for step 08: the H register, leak detection, and the ban in the prompt.

Leakage is the failure this step exists to prevent, so it is checked twice --
once as a rule the prompt states, once as a fact the gate measures.

    python skills/residual-08-holdout/scripts/run.py test
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from residual import fs, merge, profiles, prompt, registry, run, validate
from residual.config import Config
from residual.model import Stressor, Unit

STEP = "08-holdout"


def stressor(identifier: str, text: str) -> Stressor:
    return Stressor(
        id=identifier,
        lens="l",
        stressor=text,
        detection="d",
        attractor="a",
        business_reaction="b",
    )


class LeakDetectionTests(unittest.TestCase):
    def test_reworded_training_stressor_is_caught(self):
        training = [stressor("S0001", "The pricing team edits a historical tariff row without notice")]
        holdout = [
            stressor("H0001", "The pricing team edits a historic tariff row with no notice"),
            stressor("H0002", "A housing association arrives with four thousand supply points"),
        ]
        leaks = validate.leaked(holdout, training, 0.68)
        self.assertEqual([held for held, _, _ in leaks], ["H0001"])


class HoldoutStepTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".residuality"
        self.spec = registry.spec(STEP)
        self.config = Config(root=self.root)
        self.profile = profiles.Profile(vocabulary=("tariff table", "session ingest"))
        self.ctx = run.create(run.RunContext(root=self.root, slug="h", mode="loop"))

        fs.write_csv(
            self.ctx.dir / "03-stressors/register.csv",
            ("id", "lens", "stressor", "detection", "attractor", "business_reaction"),
            [
                {
                    "id": "S0001",
                    "lens": "l",
                    "stressor": "The pricing team edits a historical tariff table row without notice",
                    "detection": "d",
                    "attractor": "a",
                    "business_reaction": "b",
                }
            ],
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _gate(self, records):
        fs.write_jsonl(run.shard_path(self.ctx, self.spec, "lens"), records)
        merge.run(self.ctx, self.spec)
        return validate.run(self.ctx, self.spec, self.config, self.profile)

    def test_holdout_ids_are_distinguishable_from_training_ids(self):
        self._gate(
            [
                {
                    "stressor": "A housing association hands over four thousand supply points to session ingest at once",
                    "detection": "d",
                    "attractor": "the tariff table is rebuilt by hand",
                    "business_reaction": "b",
                }
            ]
        )
        self.assertEqual(merge.load_stressors(self.ctx, self.spec)[0].id, "H0001")

    def test_a_restated_training_stressor_fails_the_gate(self):
        gate = self._gate(
            [
                {
                    "stressor": "The pricing team edits a historic tariff table row with no notice",
                    "detection": "d",
                    "attractor": "session ingest reprices yesterday",
                    "business_reaction": "b",
                }
            ]
        )
        self.assertIn("holdout-leak", {i.code for i in gate.errors})

    def test_an_independent_stressor_does_not_leak(self):
        gate = self._gate(
            [
                {
                    "stressor": "A housing association hands over four thousand supply points to session ingest at once",
                    "detection": "d",
                    "attractor": "the tariff table is rebuilt by hand",
                    "business_reaction": "b",
                }
            ]
        )
        self.assertNotIn("holdout-leak", {i.code for i in gate.errors})
        self.assertEqual(gate.stats["leaked_rows"], 0)


class HoldoutPromptTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".residuality"
        self.ctx = run.create(run.RunContext(root=self.root, slug="hp", mode="loop"))
        self.config = Config(root=self.root)
        self.profile = profiles.Profile()

    def tearDown(self):
        self._tmp.cleanup()

    def test_prompt_names_the_files_it_must_not_open(self):
        unit = Unit(
            id=f"{STEP}--x", step=STEP, shard="x", payload={"lens": "x", "provoke": "what if"}
        )
        text = prompt.render(
            unit, registry.spec(STEP), self.ctx, self.config, self.profile
        )
        # Unlike step 09, naming them here leaks nothing: the holdout knows the
        # residues exist, it just must not read them.
        self.assertIn("03-stressors/register.csv", text)
        self.assertIn("must **not** open", text)
        self.assertIn("Do **not** read anything else", text)


if __name__ == "__main__":
    unittest.main()
