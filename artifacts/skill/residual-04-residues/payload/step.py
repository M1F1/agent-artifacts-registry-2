"""Step 04 — residue design, and the one measurement the method exists for.

Looping -- a residue reporting that an earlier one already survives its
attractor -- is counted here, never penalised. A rising looping rate is the
signal the architecture is approaching criticality (residuality-theory §looping-and-convergence), which
is why this is the only step whose prompt hands the agent what its siblings
wrote.
"""

from __future__ import annotations

from collections import Counter

from residual import fs, merge, prompt, registry
from residual.config import Config
from residual.model import (
    RESIDUE_COLUMNS,
    GateResult,
    Issue,
    Residue,
    StepSpec,
    Unit,
    residue_to_mapping,
    residue_to_row,
)
from residual.profiles import Profile
from residual.run import RunContext, compiled_path, raw_dir

SPEC = StepSpec(
    id="04-residues",
    title="Residue design",
    goal=(
        "Work one stressor into a concrete change to the naive architecture "
        "-- or record that residues written earlier already survive it, "
        "which is the looping signal for criticality (residuality-theory §looping-and-convergence)."
    ),
    skill="skills/residual-04-residues/SKILL.md",
    inputs=("02-naive/architecture.md", "03-stressors/register.csv"),
    output_template="04-residues/raw/{shard}.jsonl",
    compiled="04-residues/residues.csv",
    shard_by="batch:1",
    batch_source="03-stressors/register.csv",
    record_type="residue",
    siblings="required",
    capabilities=("context.code", "context.docs"),
)

OUTPUT_SCHEMA = """{
  "stressor_id": "the id of the stressor you were given",
  "change": "the concrete change to the architecture that survives this attractor (empty only if already survived)",
  "rationale": "why this change and not another",
  "components": ["components this introduces or modifies"],
  "already_survived_by": ["ids of earlier residues that already cover this, if any"],
  "tools_used": ["..."]
}"""

GATE_RULES = (
    "- `change` must be concrete: a named change to a named part of the "
    "architecture, not 'add validation' or 'improve monitoring'\n"
    "- if an earlier residue already survives this attractor, say so in "
    "`already_survived_by` and leave `change` empty. That is looping, and "
    "it is the result the method is looking for -- not a gap.\n"
    "- every name in `components` must be something you would be willing "
    "to see as a column in the contagion matrix"
)


def gate_rules(spec: StepSpec, config: Config, profile: Profile) -> str:
    return GATE_RULES


def compile_step(ctx: RunContext, spec: StepSpec) -> merge.CompileResult:
    """One residue per stressor, its id mirroring the stressor's.

    S0007 becomes R0007. Keeping the numbers aligned means the register and the
    residue list can be read side by side without a lookup table.
    """
    out: list[Residue] = []
    for index, parsed in enumerate(merge.parse_residues(ctx, spec), start=1):
        stressor_id = parsed.stressor_id
        identifier = (
            f"R{stressor_id[1:]}"
            if stressor_id[:1] in ("S", "H") and stressor_id[1:].isdigit()
            else f"R{index:04d}"
        )
        out.append(
            Residue(
                id=identifier,
                stressor_id=stressor_id,
                change=parsed.change,
                rationale=parsed.rationale,
                components=parsed.components,
                already_survived_by=parsed.already_survived_by,
                provenance=parsed.provenance,
            )
        )
    residues = tuple(sorted(out, key=lambda r: r.id))
    outputs = merge.write_table(
        compiled_path(ctx, spec),
        RESIDUE_COLUMNS,
        [residue_to_row(r) for r in residues],
        [residue_to_mapping(r) for r in residues],
    )
    return merge.CompileResult(
        spec.id, len(residues), merge.shard_count(ctx, spec), outputs
    )


def gate(
    ctx: RunContext, spec: StepSpec, config: Config, profile: Profile
) -> GateResult:
    """Coverage, concreteness, and the looping rate.

    Looping is not a defect to be gated away: a residue that reports being
    already survived by an earlier one is the criticality signal the whole
    method aims at (residuality-theory §looping-and-convergence). It is counted, not penalised.
    """
    residues = merge.load_residues(ctx)
    stressors = merge.load_stressors_at(ctx, "03-stressors/register.csv")
    known = {s.id for s in stressors}
    designed = {r.stressor_id for r in residues}

    issues: list[Issue] = []
    if not residues:
        issues.append(Issue(code="no-residues", detail="no residues compiled"))

    for missing in sorted(known - designed):
        issues.append(
            Issue(code="stressor-unaddressed", detail="no residue designed", where=missing)
        )
    for stray in sorted(designed - known):
        issues.append(
            Issue(
                code="unknown-stressor",
                detail=f"residue refers to {stray!r}, which is not in the register",
                where=stray,
            )
        )

    residue_ids = {r.id for r in residues}
    for residue in residues:
        if not residue.change and not residue.already_survived_by:
            issues.append(
                Issue(
                    code="empty-residue",
                    detail="no change and no claim of being already survived",
                    where=residue.id,
                )
            )
        for reference in residue.already_survived_by:
            if reference not in residue_ids:
                issues.append(
                    Issue(
                        code="dangling-loop",
                        detail=f"claims {reference!r} covers it, but no such residue exists",
                        where=residue.id,
                    )
                )

    looping = [r for r in residues if r.loops]
    components = Counter(c for r in residues for c in r.components)
    return GateResult(
        step=spec.id,
        issues=tuple(issues),
        stats={
            "residues": len(residues),
            "stressors": len(stressors),
            "looping": len(looping),
            "looping_rate": round(len(looping) / len(residues), 4) if residues else 0.0,
            "distinct_components": len(components),
            "looping_note": "high and rising means the architecture is nearing criticality",
        },
    )


def existing_residues(ctx: RunContext, spec: StepSpec) -> str:
    """Residues already written, read straight from the raw shards.

    Deliberately reads siblings: in loop mode this accumulates as the queue is
    worked, which is exactly the sequential contemplation the book describes.
    In parallel mode it shows whatever finished first -- partial, but never
    wrong, and the kernel cross-checks looping deterministically afterwards.
    """
    seen: list[str] = []
    for path in fs.iter_files(raw_dir(ctx, spec), ".jsonl"):
        for record in fs.read_jsonl(path):
            stressor_id = str(record.get("stressor_id", "")).strip()
            change = str(record.get("change", "")).strip()
            components = ", ".join(str(c) for c in (record.get("components") or []))
            if change:
                seen.append(
                    f"- `R{stressor_id[1:]}` (from {stressor_id}): {change}"
                    + (f" — components: {components}" if components else "")
                )
    if not seen:
        return "_Nothing designed yet; yours is the first._"
    return "\n".join(seen)


def prompt_context(ctx: RunContext, spec: StepSpec, unit: Unit) -> str:
    rows = list(unit.payload.get("rows") or [])
    return "\n\n".join(
        [
            "## The stressor you are working",
            prompt.rows_table(
                rows,
                ("stressor", "detection", "attractor", "business_reaction", "technical_change"),
            ),
            "## Residues already designed",
            existing_residues(ctx, spec),
        ]
    )


def report(
    ctx: RunContext, spec: StepSpec, gate_result: GateResult, profile: Profile
) -> str:
    return registry.sibling(__file__, "report").build(
        ctx, spec, merge.load_residues(ctx), gate_result
    )
