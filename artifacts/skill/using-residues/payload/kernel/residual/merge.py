"""Turning shard writes into the artifacts the analysis is read from.

Shards are written independently and never appended to a shared file, so
parallel agents cannot race each other. Compiling is what turns them into the
spreadsheets the book works from (residuality-theory §the-artifacts).

What lives here is the part every step shares: reading raw shards in
deterministic order, parsing them into typed records, writing a table, and
loading another step's compiled artifact back. What each step *does* with that
-- which identifier prefix it assigns, whether it emits a normalised JSONL
alongside the CSV, how the matrix is folded -- lives in that step's own skill,
because it is a decision about that step and nothing else.

Identifiers are assigned by the skills, never by the agents: shards are read in
sorted order and numbered, so a parallel run and a sequential run over the same
shards produce byte-identical output.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from . import fs, registry
from .model import (
    STRESSOR_COLUMNS,
    Component,
    Flow,
    Judgment,
    MatrixRow,
    Provenance,
    Residue,
    StepSpec,
    Stressor,
    component_from_mapping,
    flow_from_mapping,
    judgment_from_mapping,
    matrix_row_from_mapping,
    residue_from_mapping,
    stressor_from_mapping,
    stressor_to_mapping,
    stressor_to_row,
)
from .run import RunContext, compiled_path, raw_dir, resolve_input


@dataclass(frozen=True)
class CompileResult:
    step: str
    records: int
    shards: int
    outputs: tuple[Path, ...]


def provenance(ctx: RunContext, unit_id: str, record: Mapping[str, Any]) -> Provenance:
    return Provenance(
        unit_id=unit_id,
        mode=ctx.mode,
        harness=ctx.harness,
        model=ctx.model,
        profiles=ctx.profiles,
        tools=tuple(str(t) for t in (record.get("tools_used") or ())),
    )


def read_shards(ctx: RunContext, spec: StepSpec) -> tuple[tuple[str, dict[str, Any]], ...]:
    """Every raw record with its shard name, in deterministic order."""
    out: list[tuple[str, dict[str, Any]]] = []
    for path in fs.iter_files(raw_dir(ctx, spec), ".jsonl"):
        for record in fs.read_jsonl(path):
            out.append((path.stem, record))
    return tuple(out)


def shard_count(ctx: RunContext, spec: StepSpec) -> int:
    return len(list(fs.iter_files(raw_dir(ctx, spec))))


def write_table(
    target: Path,
    columns: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
    normalised: Iterable[Mapping[str, Any]] | None = None,
) -> tuple[Path, ...]:
    """The CSV the humans read, and optionally the JSONL the kernel reads back.

    Steps whose records carry structure a CSV cell flattens -- lists, nested
    provenance -- write both, and the loaders below prefer the JSONL.
    """
    fs.write_csv(target, columns, rows)
    if normalised is None:
        return (target,)
    jsonl = target.with_suffix(".jsonl")
    fs.write_jsonl(jsonl, normalised)
    return (target, jsonl)


# --------------------------------------------------------------------------
# parsing raw shards into typed records (no identifiers yet)
# --------------------------------------------------------------------------


def parse_stressors(ctx: RunContext, spec: StepSpec) -> tuple[Stressor, ...]:
    """Shard order preserved; ``lens`` defaults to the shard that wrote it."""
    return tuple(
        stressor_from_mapping(
            {**record, "lens": record.get("lens") or shard},
            provenance=provenance(ctx, f"{spec.id}--{shard}", record),
        )
        for shard, record in read_shards(ctx, spec)
    )


def number_stressors(
    stressors: Sequence[Stressor], prefix: str
) -> tuple[Stressor, ...]:
    """Assign register identifiers in shard order.

    Shared by the two stressor steps -- ``S`` for the training register, ``H``
    for the holdout. Numbering here rather than in the agent is what makes a
    parallel run and a sequential run produce byte-identical registers.
    """
    return tuple(
        Stressor(
            id=f"{prefix}{index:04d}",
            lens=s.lens,
            stressor=s.stressor,
            detection=s.detection,
            attractor=s.attractor,
            business_reaction=s.business_reaction,
            technical_change=s.technical_change,
            components_touched=s.components_touched,
            survived_by=s.survived_by,
            provenance=s.provenance,
        )
        for index, s in enumerate(stressors, start=1)
    )


def compile_register(ctx: RunContext, spec: StepSpec, prefix: str) -> CompileResult:
    """Compile a stressor register. Both stressor steps land here."""
    rows = number_stressors(parse_stressors(ctx, spec), prefix)
    outputs = write_table(
        compiled_path(ctx, spec),
        STRESSOR_COLUMNS,
        [stressor_to_row(r) for r in rows],
        [stressor_to_mapping(r) for r in rows],
    )
    return CompileResult(spec.id, len(rows), shard_count(ctx, spec), outputs)


def parse_flows(ctx: RunContext, spec: StepSpec) -> tuple[Flow, ...]:
    return tuple(flow_from_mapping(record) for _, record in read_shards(ctx, spec))


def parse_residues(ctx: RunContext, spec: StepSpec) -> tuple[Residue, ...]:
    return tuple(
        residue_from_mapping(
            record, provenance=provenance(ctx, f"{spec.id}--{shard}", record)
        )
        for shard, record in read_shards(ctx, spec)
    )


def parse_components(ctx: RunContext, spec: StepSpec) -> tuple[Component, ...]:
    return tuple(component_from_mapping(record) for _, record in read_shards(ctx, spec))


def parse_matrix_rows(ctx: RunContext, spec: StepSpec) -> tuple[MatrixRow, ...]:
    rows = [matrix_row_from_mapping(record) for _, record in read_shards(ctx, spec)]
    return tuple(sorted(rows, key=lambda r: r.stressor_id))


def parse_judgments(ctx: RunContext, spec: StepSpec) -> tuple[Judgment, ...]:
    parsed = [
        judgment_from_mapping(
            record, provenance=provenance(ctx, f"{spec.id}--{shard}", record)
        )
        for shard, record in read_shards(ctx, spec)
    ]
    return tuple(sorted(parsed, key=lambda j: (j.stressor_id, j.arch)))


def read_documents(ctx: RunContext, spec: StepSpec) -> str:
    parts = [
        body
        for path in fs.iter_files(raw_dir(ctx, spec), ".md")
        if (body := fs.read_text(path).strip())
    ]
    return "\n\n".join(parts) + "\n" if parts else ""


# --------------------------------------------------------------------------
# dispatch
# --------------------------------------------------------------------------


def run(ctx: RunContext, spec: StepSpec) -> CompileResult:
    """Compile a step by asking its skill to do it."""
    return registry.call(spec.id, "compile_step", ctx, spec)


# --------------------------------------------------------------------------
# reading compiled artifacts back
# --------------------------------------------------------------------------


def load_stressors(ctx: RunContext, spec: StepSpec) -> tuple[Stressor, ...]:
    path = compiled_path(ctx, spec).with_suffix(".jsonl")
    if path.exists():
        return tuple(stressor_from_mapping(r) for r in fs.read_jsonl(path))
    return tuple(stressor_from_mapping(r) for r in fs.read_csv(compiled_path(ctx, spec)))


def load_stressors_at(ctx: RunContext, relative: str) -> tuple[Stressor, ...]:
    """Load a register by path, for cross-step checks such as holdout leakage."""
    path = resolve_input(ctx, relative)
    jsonl = path.with_suffix(".jsonl")
    if jsonl.exists():
        return tuple(stressor_from_mapping(r) for r in fs.read_jsonl(jsonl))
    return tuple(stressor_from_mapping(r) for r in fs.read_csv(path))


def load_residues(ctx: RunContext) -> tuple[Residue, ...]:
    path = resolve_input(ctx, "04-residues/residues.jsonl")
    if path.exists():
        return tuple(residue_from_mapping(r) for r in fs.read_jsonl(path))
    return tuple(
        residue_from_mapping(r)
        for r in fs.read_csv(resolve_input(ctx, "04-residues/residues.csv"))
    )


def load_components(ctx: RunContext) -> tuple[Component, ...]:
    return tuple(
        component_from_mapping(r)
        for r in fs.read_csv(resolve_input(ctx, "05-architecture/components.csv"))
    )


def load_matrix_rows(ctx: RunContext, spec: StepSpec) -> tuple[MatrixRow, ...]:
    return parse_matrix_rows(ctx, spec)


def load_judgments(ctx: RunContext) -> tuple[Judgment, ...]:
    path = resolve_input(ctx, "09-ri/judgments.jsonl")
    if path.exists():
        return tuple(judgment_from_mapping(r) for r in fs.read_jsonl(path))
    return tuple(
        judgment_from_mapping(r)
        for r in fs.read_csv(resolve_input(ctx, "09-ri/judgments.csv"))
    )
