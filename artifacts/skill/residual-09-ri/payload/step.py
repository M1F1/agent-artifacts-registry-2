"""Step 09 — the empirical test: blind judging, and Ri = (Y − X) / S.

Everything about blinding is concentrated here. The prompt reproduces both
architectures inline as **A** and **B** in one normalised voice, with the
assignment derived from a hash of the run slug, and the spec forbids opening
any file under the run directory -- because a path is a label. The arithmetic
lives beside this file in ``ri.py``.
"""

from __future__ import annotations

from residual import fs, merge, prompt, registry
from residual.config import Config
from residual.model import (
    JUDGMENT_COLUMNS,
    GateResult,
    Issue,
    StepSpec,
    Unit,
    judgment_to_mapping,
    judgment_to_row,
)
from residual.profiles import Profile
from residual.run import RunContext, compiled_path, resolve_input

ri = registry.sibling(__file__, "ri")

SPEC = StepSpec(
    id="09-ri",
    title="Empirical test",
    goal=(
        "Judge, blind, whether each architecture survives each holdout "
        "stressor. The difference is the residual index Ri = (Y - X) / S."
    ),
    skill="skills/residual-09-ri/SKILL.md",
    inputs=(
        "02-naive/architecture.md",
        "05-architecture/components.csv",
        "08-holdout/register.csv",
    ),
    output_template="09-ri/raw/{shard}.jsonl",
    compiled="09-ri/judgments.csv",
    shard_by="batch:10",
    batch_source="08-holdout/register.csv",
    record_type="judgment",
    forbidden_paths=(
        "02-naive/architecture.md",
        "05-architecture/components.csv",
        "04-residues/residues.csv",
    ),
    forbidden_summary=(
        "Do not open any file under the run directory. Both architectures "
        "are reproduced in full above; anything else you could read would "
        "tell you which of them is which, and the result depends on you not "
        "knowing."
    ),
    capabilities=(),
)

OUTPUT_SCHEMA = """{
  "stressor_id": "the holdout stressor id",
  "arch": "A or B",
  "survives": true,
  "mechanism": "which part of that architecture absorbs it, and how -- required when survives is true"
}"""

GATE_RULES = (
    "- two records per stressor: one for architecture A and one for B\n"
    "- `mechanism` is required whenever `survives` is true, and must name "
    "the specific part that absorbs the stressor. 'It would probably cope' "
    "is not a judgment.\n"
    "- judge each architecture on its own terms; do not reason about which "
    "one is which"
)


def gate_rules(spec: StepSpec, config: Config, profile: Profile) -> str:
    return GATE_RULES


def compile_step(ctx: RunContext, spec: StepSpec) -> merge.CompileResult:
    judgments = merge.parse_judgments(ctx, spec)
    outputs = merge.write_table(
        compiled_path(ctx, spec),
        JUDGMENT_COLUMNS,
        [judgment_to_row(j) for j in judgments],
        [judgment_to_mapping(j) for j in judgments],
    )
    return merge.CompileResult(
        spec.id, len(judgments), merge.shard_count(ctx, spec), outputs
    )


def score(ctx: RunContext):
    """The run's Ri, computed from whatever has been judged so far."""
    judgments = merge.load_judgments(ctx)
    holdout = merge.load_stressors_at(ctx, "08-holdout/register.csv")
    return ri.score(judgments, [s.id for s in holdout], ctx.slug, blind=ctx.blind)


def gate(
    ctx: RunContext, spec: StepSpec, config: Config, profile: Profile
) -> GateResult:
    judgments = merge.load_judgments(ctx)
    result = score(ctx)

    issues: list[Issue] = []
    if not judgments:
        issues.append(Issue(code="no-judgments", detail="nothing judged"))

    for stressor_id in result.judged_one:
        issues.append(
            Issue(
                code="half-judged",
                detail="judged for one architecture only; excluded from Ri to keep the difference unbiased",
                where=stressor_id,
            )
        )
    for stressor_id in result.unjudged:
        issues.append(
            Issue(code="unjudged", detail="holdout stressor never judged", where=stressor_id)
        )
    for stressor_id, arch in result.duplicates:
        issues.append(
            Issue(
                code="duplicate-judgment",
                detail=f"architecture {arch} judged more than once; the extra was ignored",
                where=stressor_id,
                severity="warning",
            )
        )
    for judgment in judgments:
        if judgment.survives and not judgment.mechanism:
            issues.append(
                Issue(
                    code="unjustified-survival",
                    detail=(
                        "claims survival without naming the mechanism. An "
                        "unfalsifiable yes is the failure mode of LLM judging."
                    ),
                    where=f"{judgment.stressor_id}/{judgment.arch}",
                )
            )
    if not ctx.blind:
        issues.append(
            Issue(
                code="not-blind",
                detail=(
                    "this run was generated in a shared context, so Ri is not "
                    "comparable with a blind run. Reported, not blocked."
                ),
                severity="warning",
            )
        )

    return GateResult(step=spec.id, issues=tuple(issues), stats=dict(result.stats))


def architecture_blocks(ctx: RunContext) -> str:
    """Both architectures, labelled A and B, in one normalised shape.

    Presented inline so the judge never opens the source files and cannot tell
    which is which from a path. The labels come from a hash of the run slug, so
    they are reproducible but not constant across runs.
    """
    naive_body = fs.read_text(resolve_input(ctx, "02-naive/architecture.md"))
    naive_components = prompt.components_from_markdown(naive_body)
    residual_components = tuple(
        prompt.plain(f"{c.name} — {c.purpose}" if c.purpose else c.name)
        for c in merge.load_components(ctx)
    )

    labels = ri.label_map(ctx.slug)
    rendered = {
        labels["naive"]: naive_components,
        labels["residual"]: residual_components,
    }

    blocks: list[str] = []
    for label in ("A", "B"):
        items = rendered.get(label, ())
        listing = "\n".join(f"- {item}" for item in items) or "- (none listed)"
        blocks.append(f"### Architecture {label}\n\n{listing}")
    return "\n\n".join(blocks)


def prompt_context(ctx: RunContext, spec: StepSpec, unit: Unit) -> str:
    rows = list(unit.payload.get("rows") or [])
    return "\n\n".join(
        [
            "## The two architectures",
            "You are not told which is which, and you must not try to work it "
            "out. Judge each on its own terms.",
            architecture_blocks(ctx),
            "## Holdout stressors in this batch",
            prompt.rows_table(
                rows, ("stressor", "detection", "attractor", "business_reaction")
            ),
        ]
    )


def report(
    ctx: RunContext, spec: StepSpec, gate_result: GateResult, profile: Profile
) -> str:
    return registry.sibling(__file__, "report").build(ctx, spec, gate_result)


def summary(ctx: RunContext) -> tuple[tuple[str, ...], bool]:
    """What `residual ri` prints: the number, and what it does not mean."""
    result = score(ctx)
    lines = (
        f"run {ctx.slug}  mode={ctx.mode}  judge={result.judge_model or 'unrecorded'}",
        f"  S={result.stressors}  X={result.naive_survivals}  Y={result.residual_survivals}",
        f"  Ri = {result.ri:+.4f}",
        "",
        f"  {ri.interpret(result)}",
    )
    return lines, bool(result.stressors)
