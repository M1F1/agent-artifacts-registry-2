"""Tests for step 02: the control arm is assembled and reaches step 09 intact.

The gate here is deliberately thin -- no deterministic check can tell whether
an architecture document is any good. What it *can* check is that the document
exists and that the ``## Components`` bullets step 09 reads survive compiling.

    python skills/residual-02-naive/scripts/run.py test
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from residual import fs, merge, profiles, prompt, registry, run, validate
from residual.config import Config

STEP = "02-naive"

DOCUMENT = """# Naive architecture

## Components
- `OrderService` — takes orders
- `Ledger` — records them
"""


class NaiveStepTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".residuality"
        self.spec = registry.spec(STEP)
        self.config = Config(root=self.root)
        self.profile = profiles.Profile()
        self.ctx = run.create(run.RunContext(root=self.root, slug="n", mode="loop"))

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, *bodies: str):
        for index, body in enumerate(bodies, start=1):
            fs.write_text(run.shard_path(self.ctx, self.spec, f"all{index}"), body)
        merge.run(self.ctx, self.spec)
        return validate.run(self.ctx, self.spec, self.config, self.profile)

    def test_an_empty_step_fails_rather_than_passing_quietly(self):
        gate = self._run()
        self.assertFalse(gate.ok)
        self.assertIn("empty-document", {i.code for i in gate.errors})

    def test_a_written_architecture_passes(self):
        gate = self._run(DOCUMENT)
        self.assertTrue(gate.ok)
        self.assertGreater(gate.stats["characters"], 0)

    def test_shards_are_concatenated_in_order(self):
        self._run("# One\n", "# Two\n")
        body = fs.read_text(self.ctx.dir / "02-naive/architecture.md")
        self.assertLess(body.index("# One"), body.index("# Two"))

    def test_component_bullets_survive_for_the_blind_judge(self):
        self._run(DOCUMENT)
        body = fs.read_text(self.ctx.dir / "02-naive/architecture.md")
        self.assertEqual(
            prompt.components_from_markdown(body),
            ("OrderService — takes orders", "Ledger — records them"),
        )


if __name__ == "__main__":
    unittest.main()
