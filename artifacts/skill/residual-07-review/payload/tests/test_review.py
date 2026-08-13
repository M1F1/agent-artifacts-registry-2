"""Tests for step 07: the review document is assembled and gated.

Thin, like step 02's, and for the same reason: whether an FMEA is any good is
not something arithmetic can decide.

    python skills/residual-07-review/scripts/run.py test
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from residual import fs, merge, profiles, registry, run, validate
from residual.config import Config

STEP = "07-review"


class ReviewStepTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".residuality"
        self.spec = registry.spec(STEP)
        self.config = Config(root=self.root)
        self.profile = profiles.Profile()
        self.ctx = run.create(run.RunContext(root=self.root, slug="v", mode="loop"))

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, *bodies: str):
        for index, body in enumerate(bodies, start=1):
            fs.write_text(run.shard_path(self.ctx, self.spec, f"all{index}"), body)
        merge.run(self.ctx, self.spec)
        return validate.run(self.ctx, self.spec, self.config, self.profile)

    def test_a_missing_review_fails(self):
        self.assertFalse(self._run().ok)

    def test_a_written_review_passes(self):
        gate = self._run("# FMEA\n\n| Component | Failure mode |\n| --- | --- |\n| Outbox | stalls |\n")
        self.assertTrue(gate.ok)

    def test_this_step_reviews_what_the_analysis_added(self):
        self.assertIn("05-architecture/components.csv", self.spec.inputs)
        self.assertIn("06-matrix/matrix.csv", self.spec.inputs)


if __name__ == "__main__":
    unittest.main()
