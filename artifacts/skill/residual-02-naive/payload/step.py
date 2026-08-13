"""Step 02 — the naïve architecture: the control arm of the empirical test.

Its output is prose, so its gate is deliberately thin: no deterministic check
can tell whether an architecture document is any good, and a number pretending
otherwise would be worse than no number.
"""

from __future__ import annotations

from residual import fs, merge, validate
from residual.config import Config
from residual.model import GateResult, StepSpec
from residual.profiles import Profile
from residual.run import RunContext, compiled_path

SPEC = StepSpec(
    id="02-naive",
    title="Naive architecture",
    goal=(
        "Describe the smallest architecture that solves the problem exactly "
        "as stated. It is meant to be unimaginative: it is the control arm "
        "of the empirical test (residuality-theory §naive-architecture)."
    ),
    skill="skills/residual-02-naive/SKILL.md",
    inputs=("01-flows/flows.csv",),
    output_template="02-naive/raw/{shard}.md",
    compiled="02-naive/architecture.md",
    shard_by="single",
    record_type="document",
    capabilities=("context.docs",),
)

GATE_RULES = (
    "- every section filled; no placeholders\n"
    "- a `## Components` heading listing one bullet per component. Step 09 reads "
    "those bullets, so a missing heading costs you the empirical test.\n"
    "- resist improving it. Anticipating stress here contaminates the control arm."
)


def gate_rules(spec: StepSpec, config: Config, profile: Profile) -> str:
    return GATE_RULES


def compile_step(ctx: RunContext, spec: StepSpec) -> merge.CompileResult:
    body = merge.read_documents(ctx, spec)
    target = compiled_path(ctx, spec)
    fs.write_text(target, body)
    return merge.CompileResult(
        spec.id, 1 if body else 0, merge.shard_count(ctx, spec), (target,)
    )


def gate(
    ctx: RunContext, spec: StepSpec, config: Config, profile: Profile
) -> GateResult:
    return validate.document_gate(ctx, spec)
