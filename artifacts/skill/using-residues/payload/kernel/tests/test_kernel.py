"""Kernel tests: the machinery every step shares. Stdlib unittest, no deps.

Step behaviour is tested inside the step's own skill --
``skills/residual-06-matrix/tests/`` and so on. What is left here is what the
kernel owns: text similarity, the record types, profiles, the queue, sharding,
and the registry that finds the steps in the first place.

    ./bin/residual-test              # these, plus every skill's own
    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from residual import fs, paths, profiles, queue, registry, run, steps, text
from residual.config import Config
from residual.model import Unit, banned_fields_present, is_blind

BUNDLED_PROFILES = (paths.bundled_profiles(),)

#: The pipeline when every stage skill is installed. A partial install is a
#: supported arrangement, not a broken one, so tests that need a particular
#: stage say so and skip when it is absent.
FULL_PIPELINE = (
    "01-flows",
    "02-naive",
    "03-stressors",
    "04-residues",
    "05-architecture",
    "06-matrix",
    "07-review",
    "08-holdout",
    "09-ri",
)


def requires(*step_ids: str):
    installed = set(steps.step_ids())
    missing = [s for s in step_ids if s not in installed]
    return unittest.skipIf(missing, f"stage(s) not installed: {', '.join(missing)}")


class TextTests(unittest.TestCase):
    def test_similarity_separates_restatements_from_distinct_rows(self):
        a = "A regulator rules that charge session telemetry is personal data and requires deletion within 30 days."
        b = "A regulator rules that session telemetry counts as personal data and demands erasure inside 30 days."
        c = "The pricing team adds a night tariff band without announcing it."
        self.assertGreater(text.similarity(a, b), text.similarity(a, c))
        self.assertGreater(text.similarity(a, b), 0.68)
        self.assertLess(text.similarity(a, c), 0.68)

    def test_specificity_counts_only_grounded_terms(self):
        vocab = ("tariff table", "session ingest", "tariff")
        grounded = "The tariff table gains a band that session ingest misreads"
        generic = "The server goes down and users are affected"
        self.assertGreaterEqual(text.specificity(grounded, vocab), 1)
        self.assertEqual(text.specificity(generic, vocab), 0)

    def test_similarity_is_symmetric_and_bounded(self):
        a, b = "late arriving partitions", "partitions arriving late"
        self.assertAlmostEqual(text.similarity(a, b), text.similarity(b, a))
        self.assertLessEqual(text.similarity(a, b), 1.0)
        self.assertEqual(text.similarity(a, a), 1.0)


class ModelTests(unittest.TestCase):
    def test_banned_fields_are_detected_case_insensitively(self):
        self.assertEqual(banned_fields_present({"stressor": "x", "Probability": 0.4}), ("probability",))
        self.assertEqual(banned_fields_present({"stressor": "x"}), ())

    def test_blindness_follows_mode(self):
        self.assertTrue(is_blind("parallel"))
        self.assertTrue(is_blind("loop"))
        self.assertFalse(is_blind("in-session"))


class ProfileTests(unittest.TestCase):
    def test_bundled_profiles_load_and_compose(self):
        profile = profiles.load(["airflow-spark"], BUNDLED_PROFILES)
        self.assertIn("base-lenses", profile.names)
        self.assertIn("airflow-spark", profile.names)
        # domain lenses on top of the shared ones, plus one per declared role
        ids = {lens.id for lens in profiles.all_lenses(profile)}
        self.assertIn("pestle-legal", ids)
        self.assertIn("upstream-contract", ids)
        self.assertIn("role-compliance-officer", ids)

    def test_profile_shipping_answers_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.toml"
            path.write_text(
                'name = "bad"\n\n[[lens]]\nid = "x"\nprovoke = "q"\n'
                'stressors = ["the database fails"]\n',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError) as caught:
                profiles.load(["bad"], (Path(tmp),))
            self.assertIn("provocations only", str(caught.exception))

    def test_lens_without_provocation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bare.toml"
            path.write_text('name = "bare"\n\n[[lens]]\nid = "x"\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                profiles.load(["bare"], (Path(tmp),))

    def test_overlay_wins_over_base(self):
        base = profiles.Profile(names=("a",), gates={"technical_quota": 0.1})
        overlay = profiles.Profile(names=("b",), gates={"technical_quota": 0.3})
        merged = profiles.merge(base, overlay)
        self.assertEqual(merged.gates["technical_quota"], 0.3)
        self.assertEqual(merged.names, ("a", "b"))


class QueueTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ctx = run.create(
            run.RunContext(root=Path(self._tmp.name) / ".residuality", slug="t", mode="loop")
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _units(self, count: int) -> tuple[Unit, ...]:
        return tuple(
            Unit(id=f"03-stressors--l{i}", step="03-stressors", shard=f"l{i}", payload={})
            for i in range(count)
        )

    def test_claim_is_exclusive(self):
        queue.plan(self.ctx, self._units(3))
        claimed = [queue.claim(self.ctx) for _ in range(4)]
        ids = [u.id for u in claimed if u]
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(set(ids)), 3, "a unit was handed out twice")
        self.assertIsNone(claimed[3], "drained queue must return None")

    def test_drained_queue_is_the_termination_signal(self):
        queue.plan(self.ctx, self._units(1))
        unit = queue.claim(self.ctx)
        queue.complete(self.ctx, unit.id)
        self.assertIsNone(queue.claim(self.ctx))
        self.assertTrue(queue.is_drained(self.ctx))

    def test_planning_twice_does_not_duplicate_work(self):
        units = self._units(2)
        self.assertEqual(len(queue.plan(self.ctx, units)), 2)
        self.assertEqual(len(queue.plan(self.ctx, units)), 0)

    def test_failure_requeues_until_attempts_run_out(self):
        queue.plan(self.ctx, self._units(1))
        for attempt in range(1, 3):
            unit = queue.claim(self.ctx)
            self.assertIsNotNone(unit, f"expected a requeued unit on attempt {attempt}")
            _, state = queue.fail(self.ctx, unit.id, "bad output", max_attempts=3)
            self.assertEqual(state, "pending")
        unit = queue.claim(self.ctx)
        _, state = queue.fail(self.ctx, unit.id, "bad output", max_attempts=3)
        self.assertEqual(state, "failed")
        self.assertIsNone(queue.claim(self.ctx))

    def test_stale_claims_are_reclaimed(self):
        queue.plan(self.ctx, self._units(1))
        unit = queue.claim(self.ctx)
        self.assertIsNotNone(unit)
        reclaimed = queue.reclaim_stale(self.ctx, ttl_seconds=0)
        self.assertEqual(reclaimed, (unit.id,))
        self.assertIsNotNone(queue.claim(self.ctx))


class LayoutTests(unittest.TestCase):
    """The kernel ships inside a skill and finds its siblings by layout.

    These are the assumptions an install depends on: break one and a fetched
    skill stops working, which is the failure this arrangement exists to avoid.
    """

    def test_the_kernel_lives_inside_a_skill(self):
        self.assertEqual(paths.kernel_dir().name, "kernel")
        self.assertTrue((paths.skill_root() / "SKILL.md").exists())

    def test_every_step_skill_is_a_sibling_of_the_kernel_skill(self):
        root = paths.skills_root()
        self.assertEqual(paths.skill_root().parent, root)
        for spec in registry.specs():
            self.assertEqual(registry.skill_dir(spec.id).parent, root)

    def test_bundled_profiles_travel_with_the_package(self):
        bundled = paths.bundled_profiles()
        self.assertTrue(bundled.is_relative_to(paths.PACKAGE_DIR))
        self.assertTrue(any(bundled.glob("*.toml")))

    def test_an_explicit_skills_directory_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ[paths.SKILLS_ENV] = tmp
            try:
                self.assertEqual(paths.skills_root(), Path(tmp).resolve())
            finally:
                del os.environ[paths.SKILLS_ENV]
        self.assertEqual(paths.skills_root(), paths.skill_root().parent)

    def test_managed_symlink_layout_preserves_skill_siblings(self):
        with tempfile.TemporaryDirectory() as tmp:
            linked_root = Path(tmp) / "skills"
            linked_root.mkdir()
            for skill in paths.skills_root().iterdir():
                if (skill / "SKILL.md").is_file():
                    (linked_root / skill.name).symlink_to(skill, target_is_directory=True)

            environment = os.environ.copy()
            environment.pop("RESIDUAL_KERNEL", None)
            environment.pop(paths.SKILLS_ENV, None)
            command = linked_root / "residual-01-flows" / "scripts" / "run.py"
            completed = subprocess.run(
                [sys.executable, str(command), "test"],
                cwd=tmp,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(
                completed.returncode,
                0,
                completed.stdout + completed.stderr,
            )


class RegistryTests(unittest.TestCase):
    """The steps live in the skills, so finding them is kernel behaviour."""

    def test_step_skills_are_discovered_in_pipeline_order(self):
        ids = [spec.id for spec in registry.specs()]
        self.assertEqual(ids, sorted(ids), "steps must come back in pipeline order")

    @requires(*FULL_PIPELINE)
    def test_a_full_install_runs_from_flows_to_ri(self):
        ids = [spec.id for spec in registry.specs()]
        self.assertEqual(list(ids), list(FULL_PIPELINE))

    def test_a_step_declares_the_skill_it_lives_in(self):
        for spec in registry.specs():
            directory = registry.skill_dir(spec.id)
            self.assertTrue(
                (directory / "SKILL.md").exists(), f"{spec.id} has no SKILL.md"
            )
            self.assertEqual(
                spec.skill,
                f"skills/{directory.name}/SKILL.md",
                f"{spec.id} points its prompt at the wrong SKILL.md",
            )

    def test_every_step_can_compile_and_gate_itself(self):
        for spec in registry.specs():
            for required in ("compile_step", "gate"):
                self.assertTrue(
                    callable(registry.hook(spec.id, required)),
                    f"{spec.id} defines no {required}()",
                )

    def test_unknown_step_names_the_ones_that_exist(self):
        installed = steps.step_ids()
        with self.assertRaises(KeyError) as caught:
            registry.spec("42-nonsense")
        self.assertIn(installed[0], str(caught.exception))


class StepTests(unittest.TestCase):
    def test_no_step_reads_an_artifact_a_later_step_produces(self):
        """The ordering invariant, checkable however much of the pipeline is here.

        An input produced by a stage that is *not* installed is fine: someone
        hands that file over by other means, which is the whole point of a
        stage being runnable on its own.
        """
        produced_at = {spec.compiled: i for i, spec in enumerate(steps.STEPS)}
        for index, spec in enumerate(steps.STEPS):
            for required in spec.inputs:
                source = produced_at.get(required)
                if source is None:
                    continue
                self.assertLess(
                    source, index, f"{spec.id} needs {required} before it exists"
                )

    @requires(*FULL_PIPELINE)
    def test_a_full_pipeline_produces_every_artifact_it_consumes(self):
        produced: set[str] = set()
        for spec in steps.STEPS:
            for required in spec.inputs:
                self.assertIn(required, produced, f"{spec.id} needs {required} before it exists")
            produced.add(spec.compiled)

    @requires("03-stressors")
    def test_lens_sharding_yields_one_unit_per_lens(self):
        profile = profiles.load(["generic-service"], BUNDLED_PROFILES)
        spec = steps.by_id("03-stressors")
        units = steps.expand(spec, profile, Config(root=Path(".")))
        self.assertEqual(len(units), len(profiles.all_lenses(profile)))
        self.assertEqual(len({u.id for u in units}), len(units))
        self.assertTrue(all(u.payload.get("provoke") for u in units))

    @requires("03-stressors")
    def test_lens_sharding_without_lenses_is_a_clear_error(self):
        with self.assertRaises(ValueError) as caught:
            steps.expand(steps.by_id("03-stressors"), profiles.Profile(), Config(root=Path(".")))
        self.assertIn("no lenses", str(caught.exception))


@requires("04-residues", "09-ri")
class BatchShardingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / ".residuality"
        self.ctx = run.create(run.RunContext(root=self.root, slug="b", mode="loop"))
        fs.write_csv(
            self.ctx.dir / "03-stressors/register.csv",
            ("id", "stressor"),
            [{"id": f"S{i:04d}", "stressor": f"row {i}"} for i in range(1, 8)],
        )
        self.profile = profiles.Profile()

    def tearDown(self):
        self._tmp.cleanup()

    def test_batch_size_one_gives_a_unit_per_record(self):
        spec = steps.by_id("04-residues")
        units = steps.expand(spec, self.profile, Config(root=self.root), run_dir=self.ctx.dir)
        self.assertEqual(len(units), 7)
        self.assertEqual(units[0].id, "04-residues--b001")
        self.assertEqual(units[0].payload["ids"], ["S0001"])

    def test_config_can_widen_the_batch(self):
        spec = steps.by_id("04-residues")
        config = Config(root=self.root, steps={"04-residues": {"unit": "batch:3"}})
        units = steps.expand(spec, self.profile, config, run_dir=self.ctx.dir)
        self.assertEqual(len(units), 3)
        self.assertEqual(units[-1].payload["ids"], ["S0007"])

    def test_missing_source_is_a_clear_error(self):
        spec = steps.by_id("09-ri")
        with self.assertRaises(ValueError) as caught:
            steps.expand(spec, self.profile, Config(root=self.root), run_dir=self.ctx.dir)
        self.assertIn("08-holdout/register.csv", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
