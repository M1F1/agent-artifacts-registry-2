"""Step 03 — stressor analysis: random simulation, one lens per work unit.

The compile step assigns the ``S`` identifiers the rest of the pipeline refers
to. The gate is the kernel's shared stressor gate: ``08-holdout`` runs the same
one, and the two must not drift, or the empirical test would be comparing rows
judged by different standards.
"""

from __future__ import annotations

from residual import merge, prompt, validate
from residual.config import Config
from residual.model import GateResult, StepSpec
from residual.profiles import Profile
from residual.render import report as report_mod
from residual.run import RunContext

SPEC = StepSpec(
    id="03-stressors",
    title="Stressor analysis",
    goal=(
        "Randomly simulate the business environment. One row per residue: "
        "stressor, how it is detected, the attractor it pushes the business "
        "into, the business reaction, and the change to the architecture."
    ),
    skill="skills/residual-03-stressors/SKILL.md",
    inputs=("01-flows/flows.csv", "02-naive/architecture.md"),
    output_template="03-stressors/raw/{shard}.jsonl",
    compiled="03-stressors/register.csv",
    shard_by="lens",
    record_type="stressor",
    siblings="forbidden",
    capabilities=(
        "context.docs",
        "context.code",
        "context.market",
        "context.incidents",
        "context.tickets",
    ),
)

#: Identical to the holdout's, on purpose: the two registers are compared row
#: for row in step 09.
OUTPUT_SCHEMA = prompt.STRESSOR_SCHEMA

#: The ``S`` register is the training set; the holdout uses ``H``.
ID_PREFIX = "S"


def gate_rules(spec: StepSpec, config: Config, profile: Profile) -> str:
    return prompt.stressor_gate_rules(spec, config, profile)


def compile_step(ctx: RunContext, spec: StepSpec) -> merge.CompileResult:
    return merge.compile_register(ctx, spec, ID_PREFIX)


def gate(
    ctx: RunContext, spec: StepSpec, config: Config, profile: Profile
) -> GateResult:
    return validate.stressor_gate(ctx, spec, config, profile)


def report(
    ctx: RunContext, spec: StepSpec, gate_result: GateResult, profile: Profile
) -> str:
    return report_mod.stressor_report(
        ctx, spec, merge.load_stressors(ctx, spec), gate_result, profile
    )
