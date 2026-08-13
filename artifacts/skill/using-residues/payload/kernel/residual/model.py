"""Plain record types for the residuality kernel.

Nothing in this module touches the filesystem, the clock, or the network.
Every type is a frozen dataclass and every conversion is a pure function, so
the whole module is golden-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "0"

#: Separator for list-valued cells in CSV.  Not a comma, for obvious reasons.
LIST_SEP = "|"

#: Residuality bans probability, impact and cost from the analysis
#: (residuality-theory §stressors).  Keeping them out of the schema is cheaper and far
#: more reliable than keeping them out of the prompt.
BANNED_FIELDS: tuple[str, ...] = (
    "probability",
    "likelihood",
    "chance",
    "impact",
    "severity",
    "cost",
    "effort",
    "priority",
    "risk",
    "risk_score",
)

#: How a work unit was executed.  ``parallel`` gives each unit its own
#: subagent, ``loop`` restarts the agent process per unit, ``in-session`` walks
#: the queue inside a single conversation.
MODES: tuple[str, ...] = ("parallel", "loop", "in-session")


def is_blind(mode: str) -> bool:
    """Whether units run in *mode* get an uncontaminated context.

    Blindness is the property random simulation depends on: generators that can
    see each other converge (residuality-theory §random-simulation).  ``in-session`` is not blind.
    It is recorded rather than forbidden, because some harnesses cannot restart.
    """
    return mode in ("parallel", "loop")


@dataclass(frozen=True)
class Provenance:
    """What context produced a record, so the empirical test stays honest."""

    unit_id: str = ""
    mode: str = "in-session"
    harness: str = ""
    model: str = ""
    profiles: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()

    @property
    def blind(self) -> bool:
        return is_blind(self.mode)


@dataclass(frozen=True)
class Flow:
    """The movement of information between two actors (residuality-theory §flow-analysis).

    Deliberately not a process step and not a use case: those decompositions
    are the ones Parnas warned about and the book rejects.
    """

    id: str
    source: str
    target: str
    payload: str
    trigger: str
    notes: str = ""


@dataclass(frozen=True)
class Stressor:
    """One row of the stressor register; one residue.

    There is no probability, impact or cost field, and there never will be.
    """

    id: str
    lens: str
    stressor: str
    detection: str
    attractor: str
    business_reaction: str
    technical_change: str = ""
    components_touched: tuple[str, ...] = ()
    survived_by: tuple[str, ...] = ()
    provenance: Provenance = Provenance()


@dataclass(frozen=True)
class Unit:
    """A single claimable piece of work: one lens, one residue, one batch."""

    id: str
    step: str
    shard: str
    payload: Mapping[str, Any]
    attempts: int = 0


@dataclass(frozen=True)
class StepSpec:
    """The uniform contract every step obeys, whatever the harness.

    ``shard_by`` is what makes parallel and sequential execution one code path:
    it names how the step splits into independently claimable work units.
    """

    id: str
    title: str
    skill: str
    inputs: tuple[str, ...]
    output_template: str
    compiled: str
    shard_by: str
    record_type: str = "stressor"
    #: Compiled artifact chunked by ``batch:N`` sharding, one unit per chunk.
    batch_source: str = ""
    #: Whether a unit may read what its sibling shards wrote. Generation steps
    #: say ``forbidden`` because blind generators are the point; residue design
    #: says ``required`` because spotting that an earlier residue already covers
    #: this stressor *is* the looping measurement (residuality-theory §looping-and-convergence).
    siblings: str = "allowed"
    #: Artifacts a unit must not open, named in its prompt. Used to keep the
    #: holdout ignorant of the residues it is meant to test.
    forbidden_paths: tuple[str, ...] = ()
    #: Replaces the enumerated path list in the prompt. Needed where naming the
    #: files would itself leak what is being hidden -- a blind judge told not to
    #: open ``02-naive/architecture.md`` has just been told one of the two
    #: architectures is the naïve one.
    forbidden_summary: str = ""
    capabilities: tuple[str, ...] = ()
    goal: str = ""


@dataclass(frozen=True)
class Issue:
    code: str
    detail: str
    where: str = ""
    severity: str = "error"


@dataclass(frozen=True)
class GateResult:
    step: str
    issues: tuple[Issue, ...] = ()
    stats: Mapping[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.severity == "error")

    @property
    def warnings(self) -> tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.severity != "error")

    @property
    def ok(self) -> bool:
        return not self.errors


# --------------------------------------------------------------------------
# conversions
# --------------------------------------------------------------------------

FLOW_COLUMNS: tuple[str, ...] = ("id", "source", "target", "payload", "trigger", "notes")

STRESSOR_COLUMNS: tuple[str, ...] = (
    "id",
    "lens",
    "stressor",
    "detection",
    "attractor",
    "business_reaction",
    "technical_change",
    "components_touched",
    "survived_by",
    "mode",
    "blind",
    "harness",
    "model",
    "tools",
)


def split_list(value: Any) -> tuple[str, ...]:
    """Accept either a real list or a ``|``-joined cell."""
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(v).strip() for v in value if str(v).strip())
    return tuple(p.strip() for p in str(value).split(LIST_SEP) if p.strip())


def join_list(values: Sequence[str]) -> str:
    return LIST_SEP.join(values)


def provenance_from_mapping(m: Mapping[str, Any]) -> Provenance:
    return Provenance(
        unit_id=str(m.get("unit_id", "")),
        mode=str(m.get("mode", "in-session")),
        harness=str(m.get("harness", "")),
        model=str(m.get("model", "")),
        profiles=split_list(m.get("profiles")),
        tools=split_list(m.get("tools")),
    )


def flow_from_mapping(m: Mapping[str, Any]) -> Flow:
    return Flow(
        id=str(m.get("id", "")),
        source=str(m.get("source", "")).strip(),
        target=str(m.get("target", "")).strip(),
        payload=str(m.get("payload", "")).strip(),
        trigger=str(m.get("trigger", "")).strip(),
        notes=str(m.get("notes", "")).strip(),
    )


def flow_to_row(flow: Flow) -> dict[str, str]:
    return {
        "id": flow.id,
        "source": flow.source,
        "target": flow.target,
        "payload": flow.payload,
        "trigger": flow.trigger,
        "notes": flow.notes,
    }


def stressor_from_mapping(
    m: Mapping[str, Any], provenance: Provenance | None = None
) -> Stressor:
    """Build a Stressor from raw agent output.

    Unknown keys are dropped rather than rejected here; :mod:`residual.validate`
    is what reports banned fields, so that a single bad key does not lose the
    whole shard.
    """
    prov = provenance
    if prov is None:
        raw = m.get("provenance")
        prov = provenance_from_mapping(raw) if isinstance(raw, Mapping) else Provenance()
    return Stressor(
        id=str(m.get("id", "")).strip(),
        lens=str(m.get("lens", "")).strip(),
        stressor=str(m.get("stressor", "")).strip(),
        detection=str(m.get("detection", "")).strip(),
        attractor=str(m.get("attractor", "")).strip(),
        business_reaction=str(m.get("business_reaction", "")).strip(),
        technical_change=str(m.get("technical_change", "")).strip(),
        components_touched=split_list(m.get("components_touched")),
        survived_by=split_list(m.get("survived_by")),
        provenance=prov,
    )


def stressor_to_row(s: Stressor) -> dict[str, str]:
    p = s.provenance
    return {
        "id": s.id,
        "lens": s.lens,
        "stressor": s.stressor,
        "detection": s.detection,
        "attractor": s.attractor,
        "business_reaction": s.business_reaction,
        "technical_change": s.technical_change,
        "components_touched": join_list(s.components_touched),
        "survived_by": join_list(s.survived_by),
        "mode": p.mode,
        "blind": "true" if p.blind else "false",
        "harness": p.harness,
        "model": p.model,
        "tools": join_list(p.tools),
    }


def stressor_to_mapping(s: Stressor) -> dict[str, Any]:
    """Round-trippable JSON form, used for the normalised register."""
    p = s.provenance
    return {
        "id": s.id,
        "lens": s.lens,
        "stressor": s.stressor,
        "detection": s.detection,
        "attractor": s.attractor,
        "business_reaction": s.business_reaction,
        "technical_change": s.technical_change,
        "components_touched": list(s.components_touched),
        "survived_by": list(s.survived_by),
        "provenance": {
            "unit_id": p.unit_id,
            "mode": p.mode,
            "harness": p.harness,
            "model": p.model,
            "profiles": list(p.profiles),
            "tools": list(p.tools),
        },
    }


def banned_fields_present(m: Mapping[str, Any]) -> tuple[str, ...]:
    """Which banned scoring fields a raw record carries, if any."""
    lowered = {str(k).strip().lower() for k in m}
    return tuple(f for f in BANNED_FIELDS if f in lowered)


@dataclass(frozen=True)
class Residue:
    """One stressor worked up into a concrete change to the architecture.

    ``already_survived_by`` is the important field. When a residue turns out to
    be covered by residues written earlier, that is *looping* -- the signal that
    the architecture is approaching criticality (residuality-theory §looping-and-convergence). It is not
    a duplicate to be deleted; it is the measurement the whole method is aiming
    at, so it is recorded rather than discarded.
    """

    id: str
    stressor_id: str
    change: str
    rationale: str = ""
    components: tuple[str, ...] = ()
    already_survived_by: tuple[str, ...] = ()
    provenance: Provenance = Provenance()

    @property
    def loops(self) -> bool:
        return bool(self.already_survived_by)


@dataclass(frozen=True)
class Component:
    """A column of the contagion matrix: a part of the residual architecture."""

    id: str
    name: str
    kind: str = ""
    purpose: str = ""
    residues: tuple[str, ...] = ()


@dataclass(frozen=True)
class MatrixRow:
    """Which components one stressor reaches across the hyperliminal boundary."""

    stressor_id: str
    hits: tuple[str, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class Judgment:
    """One blind survival call, for the empirical test.

    ``arch`` is ``A`` or ``B``. The judge is never told which is the naïve
    architecture and which is the residual one; the mapping lives in
    :mod:`residual.ri` and is derived from the run slug.
    """

    stressor_id: str
    arch: str
    survives: bool
    mechanism: str = ""
    provenance: Provenance = Provenance()


RESIDUE_COLUMNS: tuple[str, ...] = (
    "id",
    "stressor_id",
    "change",
    "rationale",
    "components",
    "already_survived_by",
    "loops",
    "mode",
    "blind",
)

COMPONENT_COLUMNS: tuple[str, ...] = ("id", "name", "kind", "purpose", "residues")

JUDGMENT_COLUMNS: tuple[str, ...] = (
    "stressor_id",
    "arch",
    "survives",
    "mechanism",
    "mode",
    "model",
)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "y", "survives")


def residue_from_mapping(
    m: Mapping[str, Any], provenance: Provenance | None = None
) -> Residue:
    prov = provenance
    if prov is None:
        raw = m.get("provenance")
        prov = provenance_from_mapping(raw) if isinstance(raw, Mapping) else Provenance()
    return Residue(
        id=str(m.get("id", "")).strip(),
        stressor_id=str(m.get("stressor_id", "")).strip(),
        change=str(m.get("change", "")).strip(),
        rationale=str(m.get("rationale", "")).strip(),
        components=split_list(m.get("components")),
        already_survived_by=split_list(m.get("already_survived_by")),
        provenance=prov,
    )


def residue_to_row(r: Residue) -> dict[str, str]:
    return {
        "id": r.id,
        "stressor_id": r.stressor_id,
        "change": r.change,
        "rationale": r.rationale,
        "components": join_list(r.components),
        "already_survived_by": join_list(r.already_survived_by),
        "loops": "true" if r.loops else "false",
        "mode": r.provenance.mode,
        "blind": "true" if r.provenance.blind else "false",
    }


def residue_to_mapping(r: Residue) -> dict[str, Any]:
    return {
        "id": r.id,
        "stressor_id": r.stressor_id,
        "change": r.change,
        "rationale": r.rationale,
        "components": list(r.components),
        "already_survived_by": list(r.already_survived_by),
        "provenance": {
            "unit_id": r.provenance.unit_id,
            "mode": r.provenance.mode,
            "harness": r.provenance.harness,
            "model": r.provenance.model,
            "profiles": list(r.provenance.profiles),
            "tools": list(r.provenance.tools),
        },
    }


def component_from_mapping(m: Mapping[str, Any]) -> Component:
    return Component(
        id=str(m.get("id", "")).strip(),
        name=str(m.get("name", "")).strip(),
        kind=str(m.get("kind", "")).strip(),
        purpose=str(m.get("purpose", "")).strip(),
        residues=split_list(m.get("residues")),
    )


def component_to_row(c: Component) -> dict[str, str]:
    return {
        "id": c.id,
        "name": c.name,
        "kind": c.kind,
        "purpose": c.purpose,
        "residues": join_list(c.residues),
    }


def matrix_row_from_mapping(m: Mapping[str, Any]) -> MatrixRow:
    return MatrixRow(
        stressor_id=str(m.get("stressor_id", "")).strip(),
        hits=split_list(m.get("hits")),
        note=str(m.get("note", "")).strip(),
    )


def judgment_from_mapping(
    m: Mapping[str, Any], provenance: Provenance | None = None
) -> Judgment:
    prov = provenance
    if prov is None:
        raw = m.get("provenance")
        prov = provenance_from_mapping(raw) if isinstance(raw, Mapping) else Provenance()
    return Judgment(
        stressor_id=str(m.get("stressor_id", "")).strip(),
        arch=str(m.get("arch", "")).strip().upper(),
        survives=_as_bool(m.get("survives")),
        mechanism=str(m.get("mechanism", "")).strip(),
        provenance=prov,
    )


def judgment_to_row(j: Judgment) -> dict[str, str]:
    return {
        "stressor_id": j.stressor_id,
        "arch": j.arch,
        "survives": "true" if j.survives else "false",
        "mechanism": j.mechanism,
        "mode": j.provenance.mode,
        "model": j.provenance.model,
    }


def judgment_to_mapping(j: Judgment) -> dict[str, Any]:
    return {
        "stressor_id": j.stressor_id,
        "arch": j.arch,
        "survives": j.survives,
        "mechanism": j.mechanism,
        "provenance": {
            "unit_id": j.provenance.unit_id,
            "mode": j.provenance.mode,
            "harness": j.provenance.harness,
            "model": j.provenance.model,
            "profiles": list(j.provenance.profiles),
            "tools": list(j.provenance.tools),
        },
    }


def unit_to_mapping(unit: Unit) -> dict[str, Any]:
    return {
        "id": unit.id,
        "step": unit.step,
        "shard": unit.shard,
        "payload": dict(unit.payload),
        "attempts": unit.attempts,
    }


def unit_from_mapping(m: Mapping[str, Any]) -> Unit:
    return Unit(
        id=str(m["id"]),
        step=str(m["step"]),
        shard=str(m["shard"]),
        payload=dict(m.get("payload") or {}),
        attempts=int(m.get("attempts", 0)),
    )
