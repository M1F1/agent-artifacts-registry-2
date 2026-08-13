"""Step 05 — the residual architecture: every residue compressed into components.

The names this step emits become the columns of the contagion matrix and, in
step 09, the entire description a blind judge sees of the residual
architecture. So the gate is about names and provenance: a component nobody's
residue asked for, or a residue whose component was quietly dropped.
"""

from __future__ import annotations

from residual import merge
from residual.config import Config
from residual.model import (
    COMPONENT_COLUMNS,
    Component,
    GateResult,
    Issue,
    StepSpec,
    component_to_row,
)
from residual.profiles import Profile
from residual.run import RunContext, compiled_path

SPEC = StepSpec(
    id="05-architecture",
    title="Residual architecture",
    goal=(
        "Compress every residue into one coherent architecture and name its "
        "components. These names become the columns of the contagion matrix."
    ),
    skill="skills/residual-05-architecture/SKILL.md",
    inputs=(
        "02-naive/architecture.md",
        "03-stressors/register.csv",
        "04-residues/residues.csv",
    ),
    output_template="05-architecture/raw/{shard}.jsonl",
    compiled="05-architecture/components.csv",
    shard_by="single",
    record_type="component",
    capabilities=("context.docs",),
)

OUTPUT_SCHEMA = """{
  "name": "short, stable noun -- this becomes a matrix column",
  "kind": "one of the profile's component kinds",
  "purpose": "one line on what it is for",
  "residues": ["residue ids that forced this component to exist"]
}"""

GATE_RULES = (
    "- every component needs a `purpose` and at least one driving residue\n"
    "- names must be stable nouns; they become matrix columns and are "
    "matched exactly\n"
    "- do not invent components no residue asked for"
)


def gate_rules(spec: StepSpec, config: Config, profile: Profile) -> str:
    return GATE_RULES


def compile_step(ctx: RunContext, spec: StepSpec) -> merge.CompileResult:
    """Sorted by name, so the matrix columns are stable across runs."""
    parsed = sorted(merge.parse_components(ctx, spec), key=lambda c: c.name.lower())
    components = tuple(
        Component(
            id=f"C{index:03d}",
            name=c.name,
            kind=c.kind,
            purpose=c.purpose,
            residues=c.residues,
        )
        for index, c in enumerate(parsed, start=1)
    )
    outputs = merge.write_table(
        compiled_path(ctx, spec),
        COMPONENT_COLUMNS,
        [component_to_row(c) for c in components],
    )
    return merge.CompileResult(
        spec.id, len(components), merge.shard_count(ctx, spec), outputs
    )


def gate(
    ctx: RunContext, spec: StepSpec, config: Config, profile: Profile
) -> GateResult:
    components = merge.load_components(ctx)
    residues = merge.load_residues(ctx)
    names = {c.name for c in components}
    residue_ids = {r.id for r in residues}

    issues: list[Issue] = []
    if not components:
        issues.append(Issue(code="no-components", detail="no components compiled"))

    for component in components:
        if not component.purpose:
            issues.append(
                Issue(code="empty-purpose", detail="no purpose given", where=component.name)
            )
        unknown = [r for r in component.residues if r not in residue_ids]
        if unknown:
            issues.append(
                Issue(
                    code="unknown-residue",
                    detail=f"cites {', '.join(unknown)}, which do not exist",
                    where=component.name,
                    severity="warning",
                )
            )
        if not component.residues:
            issues.append(
                Issue(
                    code="undriven-component",
                    detail="no residue asked for this component",
                    where=component.name,
                    severity="warning",
                )
            )

    asked_for = {c for r in residues for c in r.components}
    dropped = sorted(asked_for - names)
    for name in dropped:
        issues.append(
            Issue(
                code="residue-component-dropped",
                detail="a residue named this component but the architecture has no such column",
                where=name,
                severity="warning",
            )
        )

    return GateResult(
        step=spec.id,
        issues=tuple(issues),
        stats={
            "components": len(components),
            "residues": len(residues),
            "components_dropped": len(dropped),
        },
    )
