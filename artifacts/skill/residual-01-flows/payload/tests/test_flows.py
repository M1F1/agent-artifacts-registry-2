"""Tests for step 01: flow numbering, and the gate that keeps later steps honest.

The flows are the vocabulary every later specificity gate measures against, so
an incomplete flow here weakens a gate three steps away. That is what these
tests are protecting.

    python skills/residual-01-flows/scripts/run.py test
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from residual import fs, merge, profiles, registry, run, validate
from residual.config import Config

STEP = "01-flows"

FLOW = {
    "source": "Meter operator",
    "target": "Ingest DAG",
    "payload": "half-hourly meter reads",
    "trigger": "daily at 04:00",
}


class FlowStepTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".residuality"
        self.spec = registry.spec(STEP)
        self.config = Config(root=self.root)
        self.profile = profiles.Profile()
        self.ctx = run.create(run.RunContext(root=self.root, slug="f", mode="loop"))

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, records):
        fs.write_jsonl(run.shard_path(self.ctx, self.spec, "all"), records)
        merge.run(self.ctx, self.spec)
        return validate.run(self.ctx, self.spec, self.config, self.profile)

    def test_flows_are_numbered_in_shard_order(self):
        self._run([FLOW, {**FLOW, "payload": "settlement corrections"}])
        rows = fs.read_csv(self.ctx.dir / "01-flows/flows.csv")
        self.assertEqual([r["id"] for r in rows], ["F0001", "F0002"])

    def test_a_flow_missing_what_moves_is_an_error(self):
        gate = self._run([{**FLOW, "payload": ""}])
        self.assertIn("empty-field", {i.code for i in gate.errors})

    def test_actors_are_counted_from_both_ends(self):
        gate = self._run([FLOW, {**FLOW, "source": "Ingest DAG", "target": "Settlement job"}])
        self.assertEqual(gate.stats["records"], 2)
        self.assertEqual(gate.stats["actors"], 3)

    def test_no_flows_at_all_fails(self):
        self.assertFalse(self._run([]).ok)

    def test_this_step_reads_nothing_so_it_can_run_alone(self):
        self.assertEqual(self.spec.inputs, ())


if __name__ == "__main__":
    unittest.main()
