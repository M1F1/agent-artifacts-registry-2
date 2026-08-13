"""Tests for step 09: the arithmetic, the caveats, and the blinding.

The blinding tests are the load-bearing ones. If the prompt names a file under
the run directory, or renders one architecture in a different voice from the
other, the judge can work out which is which and Ri stops meaning anything.

    python skills/residual-09-ri/scripts/run.py test
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from residual import fs, profiles, prompt, registry, run, validate
from residual.config import Config
from residual.model import Judgment, Provenance, Unit

STEP = "09-ri"
ri = registry.sibling_of(STEP, "ri")


def judgment(stressor_id: str, arch: str, survives: bool) -> Judgment:
    return Judgment(
        stressor_id=stressor_id,
        arch=arch,
        survives=survives,
        mechanism="named component absorbs it" if survives else "",
        provenance=Provenance(model="fixture"),
    )


class RiTests(unittest.TestCase):
    def test_label_map_is_deterministic_and_not_constant(self):
        self.assertEqual(ri.label_map("alpha"), ri.label_map("alpha"))
        maps = {tuple(sorted(ri.label_map(s).items())) for s in
                ("alpha", "beta", "gamma", "delta", "epsilon", "zeta")}
        self.assertEqual(len(maps), 2, "labels never flip across runs")

    def test_architecture_of_inverts_the_label_map(self):
        labels = ri.label_map("northwind")
        self.assertEqual(ri.architecture_of("northwind", labels["naive"]), "naive")
        self.assertEqual(ri.architecture_of("northwind", labels["residual"]), "residual")
        with self.assertRaises(ValueError):
            ri.architecture_of("northwind", "C")

    def test_ri_arithmetic(self):
        labels = ri.label_map("run")
        judgments = []
        for i in range(1, 11):
            judgments.append(judgment(f"H{i:04d}", labels["naive"], i <= 2))
            judgments.append(judgment(f"H{i:04d}", labels["residual"], i <= 7))
        result = ri.score(judgments, [f"H{i:04d}" for i in range(1, 11)], "run")
        self.assertEqual((result.stressors, result.naive_survivals, result.residual_survivals), (10, 2, 7))
        self.assertAlmostEqual(result.ri, 0.5)

    def test_half_judged_stressors_are_excluded_not_counted(self):
        labels = ri.label_map("run")
        judgments = [
            judgment("H0001", labels["naive"], False),
            judgment("H0001", labels["residual"], True),
            judgment("H0002", labels["residual"], True),  # no counterpart
        ]
        result = ri.score(judgments, ["H0001", "H0002"], "run")
        self.assertEqual(result.stressors, 1)
        self.assertEqual(result.judged_one, ("H0002",))
        self.assertAlmostEqual(result.ri, 1.0)

    def test_unjudged_holdout_is_reported(self):
        result = ri.score([], ["H0001", "H0002"], "run")
        self.assertEqual(result.unjudged, ("H0001", "H0002"))
        self.assertEqual(result.ri, 0.0)
        self.assertIn("undefined", ri.interpret(result))

    def test_interpretation_carries_the_caveats(self):
        labels = ri.label_map("run")
        judgments = [
            judgment("H0001", labels["naive"], False),
            judgment("H0001", labels["residual"], True),
        ]
        blind = ri.interpret(ri.score(judgments, ["H0001"], "run", blind=True))
        unblind = ri.interpret(ri.score(judgments, ["H0001"], "run", blind=False))
        self.assertIn("one judge model", blind)
        self.assertNotIn("NOT blind", blind)
        self.assertIn("NOT blind", unblind)


class JudgingTests(unittest.TestCase):
    """The prompt and the gate, on a run with both architectures on disk."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".residuality"
        self.spec = registry.spec(STEP)
        self.config = Config(root=self.root)
        self.profile = profiles.Profile()
        self.ctx = run.create(run.RunContext(root=self.root, slug="iso", mode="loop"))

        fs.write_text(
            self.ctx.dir / "02-naive/architecture.md",
            "# Naive\n\n## Components\n- `OrderService` — takes orders\n- `Ledger` — records them\n",
        )
        fs.write_csv(
            self.ctx.dir / "05-architecture/components.csv",
            ("id", "name", "kind", "purpose", "residues"),
            [
                {"id": "C001", "name": "OrderService", "kind": "service", "purpose": "takes orders", "residues": "R1"},
                {"id": "C002", "name": "VersionedPriceStore", "kind": "datastore", "purpose": "pins prices", "residues": "R2"},
                {"id": "C003", "name": "Outbox", "kind": "queue", "purpose": "buffers sends", "residues": "R3"},
            ],
        )
        fs.write_csv(
            self.ctx.dir / "08-holdout/register.csv",
            ("id", "lens", "stressor", "detection", "attractor", "business_reaction"),
            [{"id": "H0001", "lens": "l", "stressor": "s", "detection": "d", "attractor": "a", "business_reaction": "b"}],
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _render(self) -> str:
        unit = Unit(
            id=f"{STEP}--b001",
            step=STEP,
            shard="b001",
            payload={"ids": ["H0001"], "rows": [{"id": "H0001", "stressor": "s"}]},
        )
        return prompt.render(unit, self.spec, self.ctx, self.config, self.profile)

    def test_prompt_never_names_the_architecture_files(self):
        text = self._render()
        for leak in ("02-naive", "05-architecture", "architecture.md", "components.csv"):
            self.assertNotIn(leak, text, f"blinding leak: prompt names {leak}")

    def test_both_architectures_are_rendered_in_one_voice(self):
        text = self._render()
        block_a = text.split("### Architecture A", 1)[1].split("### Architecture B")[0]
        block_b = text.split("### Architecture B", 1)[1].split("\n##", 1)[0]
        self.assertNotIn("`", block_a, "markdown styling survives and tells them apart")
        self.assertNotIn("`", block_b)
        self.assertTrue(block_a.strip() and block_b.strip())

    def test_survival_without_a_mechanism_fails_the_gate(self):
        labels = ri.label_map(self.ctx.slug)
        fs.write_jsonl(
            run.shard_path(self.ctx, self.spec, "b001"),
            [
                {"stressor_id": "H0001", "arch": labels["naive"], "survives": False},
                {"stressor_id": "H0001", "arch": labels["residual"], "survives": True},
            ],
        )
        from residual import merge

        merge.run(self.ctx, self.spec)
        gate = validate.run(self.ctx, self.spec, self.config, self.profile)
        self.assertIn("unjustified-survival", {i.code for i in gate.errors})

    def test_summary_reports_undefined_ri_before_anything_is_judged(self):
        lines, ok = registry.call(STEP, "summary", self.ctx)
        self.assertFalse(ok)
        self.assertIn("undefined", "\n".join(lines))


if __name__ == "__main__":
    unittest.main()
