"""Tests for step 05: stable component names and their provenance in residues.

These names become matrix columns and, in step 09, the whole description a
blind judge sees. So the tests are about names surviving the trip intact.

    python skills/residual-05-architecture/scripts/run.py test
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from residual import fs, merge, profiles, registry, run, validate
from residual.config import Config

STEP = "05-architecture"


class ArchitectureStepTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".residuality"
        self.spec = registry.spec(STEP)
        self.config = Config(root=self.root)
        self.profile = profiles.Profile()
        self.ctx = run.create(run.RunContext(root=self.root, slug="a", mode="loop"))

        fs.write_csv(
            self.ctx.dir / "04-residues/residues.csv",
            ("id", "stressor_id", "change", "rationale", "components", "already_survived_by"),
            [
                {"id": "R0001", "stressor_id": "S0001", "change": "pin prices", "rationale": "r", "components": "PriceStore", "already_survived_by": ""},
                {"id": "R0002", "stressor_id": "S0002", "change": "buffer sends", "rationale": "r", "components": "Outbox", "already_survived_by": ""},
            ],
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, records):
        fs.write_jsonl(run.shard_path(self.ctx, self.spec, "all"), records)
        merge.run(self.ctx, self.spec)
        return validate.run(self.ctx, self.spec, self.config, self.profile)

    def test_components_are_sorted_so_matrix_columns_are_stable(self):
        self._run(
            [
                {"name": "Outbox", "kind": "queue", "purpose": "buffers sends", "residues": ["R0002"]},
                {"name": "PriceStore", "kind": "datastore", "purpose": "pins prices", "residues": ["R0001"]},
            ]
        )
        rows = fs.read_csv(self.ctx.dir / "05-architecture/components.csv")
        self.assertEqual([r["name"] for r in rows], ["Outbox", "PriceStore"])
        self.assertEqual([r["id"] for r in rows], ["C001", "C002"])

    def test_a_component_no_residue_asked_for_is_flagged(self):
        gate = self._run(
            [
                {"name": "PriceStore", "kind": "datastore", "purpose": "pins prices", "residues": ["R0001"]},
                {"name": "Outbox", "kind": "queue", "purpose": "buffers sends", "residues": ["R0002"]},
                {"name": "ServiceMesh", "kind": "service", "purpose": "because", "residues": []},
            ]
        )
        undriven = {i.where for i in gate.warnings if i.code == "undriven-component"}
        self.assertEqual(undriven, {"ServiceMesh"})

    def test_a_residues_component_quietly_dropped_is_flagged(self):
        gate = self._run(
            [{"name": "PriceStore", "kind": "datastore", "purpose": "pins prices", "residues": ["R0001"]}]
        )
        dropped = {i.where for i in gate.warnings if i.code == "residue-component-dropped"}
        self.assertEqual(dropped, {"Outbox"})
        self.assertEqual(gate.stats["components_dropped"], 1)

    def test_a_component_without_a_purpose_is_an_error(self):
        gate = self._run(
            [
                {"name": "PriceStore", "kind": "datastore", "purpose": "", "residues": ["R0001"]},
                {"name": "Outbox", "kind": "queue", "purpose": "buffers sends", "residues": ["R0002"]},
            ]
        )
        self.assertIn("empty-purpose", {i.code for i in gate.errors})


if __name__ == "__main__":
    unittest.main()
