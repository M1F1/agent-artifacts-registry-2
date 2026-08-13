"""Tests for step 06: the matrix arithmetic and the gate over it.

    python skills/residual-06-matrix/scripts/run.py test
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from residual import fs, merge, profiles, registry, run, validate
from residual.config import Config
from residual.model import Component, MatrixRow

STEP = "06-matrix"
matrix = registry.sibling_of(STEP, "matrix")


def component(name: str) -> Component:
    return Component(id=name, name=name, purpose="p", residues=("R0001",))


def row(stressor: str, *hits: str) -> MatrixRow:
    return MatrixRow(stressor_id=stressor, hits=hits)


class MatrixTests(unittest.TestCase):
    def setUp(self):
        self.components = [component(n) for n in ("Alpha", "Beta", "Gamma", "Delta")]
        self.rows = [
            row("S0001", "Alpha", "Beta"),
            row("S0002", "Alpha", "Beta"),
            row("S0003", "Gamma"),
            row("S0004"),
        ]
        self.matrix = matrix.build(self.rows, self.components)

    def test_totals(self):
        self.assertEqual(self.matrix.row_total("S0001"), 2)
        self.assertEqual(self.matrix.row_total("S0004"), 0)
        self.assertEqual(self.matrix.column_total("Alpha"), 2)
        self.assertEqual(self.matrix.column_total("Delta"), 0)

    def test_unknown_components_are_dropped_not_invented(self):
        rows = [row("S0001", "Alpha", "NotAComponent")]
        built = matrix.build(rows, self.components)
        self.assertEqual(built.row_total("S0001"), 1)
        self.assertEqual(
            matrix.unknown_components(rows, self.components),
            (("S0001", "NotAComponent"),),
        )

    def test_coupling_pairs_rank_by_shared_stress(self):
        pairs = matrix.coupling_pairs(self.matrix)
        self.assertEqual(pairs[0], ("Alpha", "Beta", 2))

    def test_merge_candidates_need_identical_and_non_empty_signatures(self):
        groups = matrix.merge_candidates(self.matrix)
        self.assertIn(("Alpha", "Beta"), groups)
        # Delta and any other untouched column match trivially and must not be
        # offered as a merge candidate.
        self.assertTrue(all("Delta" not in group for group in groups))

    def test_triggers_report_n_k_and_the_empty_edges(self):
        t = matrix.triggers(self.matrix)
        self.assertEqual(t.k, 5)
        self.assertEqual(t.n, len(self.matrix.stressors) + len(self.matrix.components))
        self.assertEqual(t.untouched_components, ("Delta",))
        self.assertEqual(t.unmapped_stressors, ("S0004",))

    def test_csv_shape_matches_the_books_table(self):
        columns = matrix.columns(self.matrix)
        self.assertEqual(columns[0], "stressor")
        self.assertEqual(columns[-1], "total")
        rows = matrix.to_rows(self.matrix)
        self.assertEqual(rows[-1]["stressor"], "TOTAL")
        self.assertEqual(rows[-1]["Alpha"], "2")


class MatrixStepTests(unittest.TestCase):
    """The step end to end: shards in, matrix.csv out, gate findings back."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".residuality"
        self.spec = registry.spec(STEP)
        self.config = Config(root=self.root)
        self.profile = profiles.Profile()
        self.ctx = run.create(run.RunContext(root=self.root, slug="m", mode="loop"))

        fs.write_csv(
            self.ctx.dir / "05-architecture/components.csv",
            ("id", "name", "kind", "purpose", "residues"),
            [
                {"id": "C001", "name": "Alpha", "kind": "service", "purpose": "p", "residues": "R0001"},
                {"id": "C002", "name": "Beta", "kind": "service", "purpose": "p", "residues": "R0002"},
            ],
        )
        fs.write_csv(
            self.ctx.dir / "03-stressors/register.csv",
            ("id", "lens", "stressor", "detection", "attractor", "business_reaction"),
            [
                {"id": "S0001", "lens": "l", "stressor": "s1", "detection": "d", "attractor": "a", "business_reaction": "b"},
                {"id": "S0002", "lens": "l", "stressor": "s2", "detection": "d", "attractor": "a", "business_reaction": "b"},
            ],
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, records):
        fs.write_jsonl(run.shard_path(self.ctx, self.spec, "b001"), records)
        merge.run(self.ctx, self.spec)
        return validate.run(self.ctx, self.spec, self.config, self.profile)

    def test_compiled_csv_carries_the_totals_row(self):
        self._run(
            [
                {"stressor_id": "S0001", "hits": ["Alpha"]},
                {"stressor_id": "S0002", "hits": ["Alpha", "Beta"]},
            ]
        )
        rows = fs.read_csv(self.ctx.dir / "06-matrix/matrix.csv")
        self.assertEqual(rows[-1]["stressor"], "TOTAL")
        self.assertEqual(rows[-1]["Alpha"], "2")

    def test_a_component_no_stressor_reaches_is_trigger_seven(self):
        gate = self._run([{"stressor_id": "S0001", "hits": ["Alpha"]}, {"stressor_id": "S0002", "hits": ["Alpha"]}])
        untouched = [i for i in gate.warnings if i.code == "untouched-component"]
        self.assertEqual([i.where for i in untouched], ["Beta"])

    def test_naming_a_component_that_does_not_exist_is_an_error(self):
        gate = self._run(
            [
                {"stressor_id": "S0001", "hits": ["Ghost"]},
                {"stressor_id": "S0002", "hits": ["Alpha", "Beta"]},
            ]
        )
        self.assertIn("unknown-component", {i.code for i in gate.errors})

    def test_a_stressor_with_no_row_is_reported(self):
        gate = self._run([{"stressor_id": "S0001", "hits": ["Alpha", "Beta"]}])
        unmapped = {i.where for i in gate.errors if i.code == "stressor-unmapped"}
        self.assertEqual(unmapped, {"S0002"})


if __name__ == "__main__":
    unittest.main()
