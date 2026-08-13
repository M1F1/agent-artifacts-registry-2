"""Step 08 — the holdout: stressors that were never used to design anything.

This is the test set of the empirical test, and it is worthless the moment it
has seen the residues. Two mechanisms keep it honest, and both live here: the
spec forbids opening any downstream artifact, and the gate measures leakage
against the training register afterwards -- because a rule in a prompt is a
request, while a check on the output is a fact.
"""

from __future__ import annotations

from residual import config as config_mod
from residual import merge, prompt, validate
from residual.config import Config
from residual.model import GateResult, Issue, StepSpec
from residual.profiles import Profile
from residual.render import report as report_mod
from residual.run import RunContext

SPEC = StepSpec(
    id="08-holdout",
    title="Holdout stressors",
    goal=(
        "Generate stressors that were never used to design anything. This is "
        "the test set of the empirical test, and it is worthless if it has "
        "seen the residues (residuality-theory §empirical-test)."
    ),
    skill="skills/residual-08-holdout/SKILL.md",
    inputs=("01-flows/flows.csv",),
    output_template="08-holdout/raw/{shard}.jsonl",
    compiled="08-holdout/register.csv",
    shard_by="lens",
    record_type="stressor",
    siblings="forbidden",
    forbidden_paths=(
        "03-stressors/register.csv",
        "04-residues/residues.csv",
        "05-architecture/components.csv",
        "07-review/review.md",
    ),
    capabilities=(
        "context.docs",
        "context.code",
        "context.market",
        "context.incidents",
    ),
)

#: The same record the training register carries. Sharing the schema is what
#: makes leak detection a like-for-like comparison.
OUTPUT_SCHEMA = prompt.STRESSOR_SCHEMA

ID_PREFIX = "H"


def gate_rules(spec: StepSpec, config: Config, profile: Profile) -> str:
    return prompt.stressor_gate_rules(spec, config, profile) + (
        "\n- no record may restate a stressor from the training register. You "
        "have not seen it and must not go looking; the gate compares yours "
        "against it afterwards."
    )


def compile_step(ctx: RunContext, spec: StepSpec) -> merge.CompileResult:
    return merge.compile_register(ctx, spec, ID_PREFIX)


def gate(
    ctx: RunContext, spec: StepSpec, config: Config, profile: Profile
) -> GateResult:
    """The shared stressor gate, plus the check the empirical test rests on."""
    base = validate.stressor_gate(ctx, spec, config, profile)

    holdout = merge.load_stressors(ctx, spec)
    training = merge.load_stressors_at(ctx, "03-stressors/register.csv")
    threshold = float(config_mod.gate(config, "duplicate_threshold", spec.id))
    leaks = validate.leaked(holdout, training, threshold)

    issues = list(base.issues) + [
        Issue(
            code="holdout-leak",
            detail=(
                f"{held} restates training stressor {trained} (score {score:.2f}). "
                "A holdout that has seen the residues inflates Ri without the "
                "architecture having earned it."
            ),
            where=held,
        )
        for held, trained, score in leaks
    ]

    stats = dict(base.stats)
    stats.update(
        {
            "training_stressors": len(training),
            "leaked_rows": len(leaks),
            "leak_note": "lexical only; a reworded leak in different vocabulary is not detected",
        }
    )
    return GateResult(step=spec.id, issues=tuple(issues), stats=stats)


def report(
    ctx: RunContext, spec: StepSpec, gate_result: GateResult, profile: Profile
) -> str:
    return report_mod.stressor_report(
        ctx, spec, merge.load_stressors(ctx, spec), gate_result, profile
    )
