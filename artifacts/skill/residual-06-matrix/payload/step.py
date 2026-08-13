"""Step 06 — contagion analysis: stressors against components.

The arithmetic lives beside this file in ``matrix.py`` and belongs to this step
alone. No model ever computes a total: a model that miscounts a column produces
a plausible-looking refactoring plan built on a wrong number.
"""

from __future__ import annotations

from residual import merge, prompt, registry
from residual.config import Config
from residual.model import GateResult, Issue, StepSpec, Unit
from residual.profiles import Profile
from residual.run import RunContext, compiled_path

matrix = registry.sibling(__file__, "matrix")

SPEC = StepSpec(
    id="06-matrix",
    title="Contagion analysis",
    goal=(
        "For each stressor, mark every component it reaches. The matrix maps "
        "the frictions across the hyperliminal boundary, not the domain "
        "(residuality-theory §contagion-analysis)."
    ),
    skill="skills/residual-06-matrix/SKILL.md",
    inputs=("03-stressors/register.csv", "05-architecture/components.csv"),
    output_template="06-matrix/raw/{shard}.jsonl",
    compiled="06-matrix/matrix.csv",
    shard_by="batch:20",
    batch_source="03-stressors/register.csv",
    record_type="matrix",
    capabilities=(),
)

OUTPUT_SCHEMA = """{
  "stressor_id": "the id of the stressor",
  "hits": ["every component this stressor reaches"],
  "note": "anything surprising about the row (optional)"
}"""

GATE_RULES = (
    "- every stressor in your batch needs exactly one row, even if `hits` "
    "is empty\n"
    "- every name in `hits` must match a component name exactly; unknown "
    "names fail the gate rather than creating a column"
)


def gate_rules(spec: StepSpec, config: Config, profile: Profile) -> str:
    return GATE_RULES


def compile_step(ctx: RunContext, spec: StepSpec) -> merge.CompileResult:
    """Fold the rows into the book's table, totals included."""
    rows = merge.parse_matrix_rows(ctx, spec)
    built = matrix.build(rows, merge.load_components(ctx))
    outputs = merge.write_table(
        compiled_path(ctx, spec), matrix.columns(built), matrix.to_rows(built)
    )
    return merge.CompileResult(spec.id, len(rows), merge.shard_count(ctx, spec), outputs)


def gate(
    ctx: RunContext, spec: StepSpec, config: Config, profile: Profile
) -> GateResult:
    rows = merge.load_matrix_rows(ctx, spec)
    components = merge.load_components(ctx)
    stressors = merge.load_stressors_at(ctx, "03-stressors/register.csv")

    issues: list[Issue] = []
    if not rows:
        issues.append(Issue(code="empty-matrix", detail="no matrix rows compiled"))

    covered = {r.stressor_id for r in rows}
    for missing in sorted({s.id for s in stressors} - covered):
        issues.append(Issue(code="stressor-unmapped", detail="no matrix row", where=missing))

    for stressor_id, name in matrix.unknown_components(rows, components):
        issues.append(
            Issue(
                code="unknown-component",
                detail=f"{name!r} is not a component; the cell was dropped rather than inventing a column",
                where=stressor_id,
            )
        )

    built = matrix.build(rows, components)
    triggers = matrix.triggers(built)

    for name in triggers.untouched_components:
        issues.append(
            Issue(
                code="untouched-component",
                detail=(
                    "no stressor reaches this component. Trigger 7: more likely "
                    "you have not stressed this part enough than that it is "
                    "invulnerable (residuality-theory §contagion-analysis)."
                ),
                where=name,
                severity="warning",
            )
        )
    for stressor_id in triggers.unmapped_stressors:
        issues.append(
            Issue(
                code="inert-stressor",
                detail="reaches no component at all — either genuinely non-technical, or the row was skipped",
                where=stressor_id,
                severity="warning",
            )
        )

    return GateResult(step=spec.id, issues=tuple(issues), stats=dict(triggers.stats))


def prompt_context(ctx: RunContext, spec: StepSpec, unit: Unit) -> str:
    rows = list(unit.payload.get("rows") or [])
    components = "\n".join(f"- `{c.name}`" for c in merge.load_components(ctx))
    return "\n\n".join(
        [
            "## Components (use these names exactly)",
            components or "_No components compiled yet._",
            "## Stressors in this batch",
            prompt.rows_table(rows, ("stressor", "attractor", "technical_change")),
        ]
    )


def report(
    ctx: RunContext, spec: StepSpec, gate_result: GateResult, profile: Profile
) -> str:
    rows = merge.load_matrix_rows(ctx, spec)
    built = matrix.build(rows, merge.load_components(ctx))
    return registry.sibling(__file__, "report").build(
        ctx, spec, built, matrix.triggers(built), gate_result
    )
