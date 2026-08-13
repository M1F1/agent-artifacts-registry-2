"""Step 07 — FMEA and ATAM over what the earlier steps introduced.

The residues added components, and components fail and cost money. This step
exists so the analysis reviews its own output rather than only the system it
started from (residuality-theory §fmea-atam). Like step 02 its artifact is prose, so its
gate only checks that the document exists.
"""

from __future__ import annotations

from residual import fs, merge, validate
from residual.config import Config
from residual.model import GateResult, StepSpec
from residual.profiles import Profile
from residual.run import RunContext, compiled_path

SPEC = StepSpec(
    id="07-review",
    title="FMEA and ATAM review",
    goal=(
        "Catch what the earlier steps introduced: technical failure modes "
        "from the added components, and the political and cost trade-offs "
        "between residues (residuality-theory §fmea-atam)."
    ),
    skill="skills/residual-07-review/SKILL.md",
    inputs=(
        "05-architecture/components.csv",
        "06-matrix/matrix.csv",
    ),
    output_template="07-review/raw/{shard}.md",
    compiled="07-review/review.md",
    shard_by="single",
    record_type="document",
    capabilities=("context.docs",),
)

GATE_RULES = (
    "- every section filled; no placeholders\n"
    "- FMEA rows name a component that exists in `05-architecture/components.csv`\n"
    "- this is the one step where cost and priority are allowed. They were "
    "banned during simulation so they could not filter it; here the "
    "simulation is over."
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
