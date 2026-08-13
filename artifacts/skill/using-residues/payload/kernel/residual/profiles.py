"""Domain profiles: what kind of system is under analysis.

A profile tells the steps what a *component* is in this world, where to look for
flows, which lenses shard the stressor generation, and which gate thresholds
make sense here.  That is what lets one pipeline run against a Spring service
mesh and an Airflow/Spark platform without forking the steps.

A profile ships **provocations, never stressors**.  A profile carrying concrete
stressors would turn this framework into the generic pattern checklist the
theory rejects (residuality-theory §stressors), and every platform in the company would
produce the same forty rows.  :func:`load` refuses to load one that tries.

Profiles compose: a public technology profile plus a private workplace overlay
carrying your real teams, regulators and upstream systems.  The overlay lives in
``.residuality/profiles`` and is never committed to the shared framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from . import fs

#: Keys that would smuggle answers into a profile.  Loading fails on these.
BANNED_PROFILE_KEYS: tuple[str, ...] = (
    "stressor",
    "stressors",
    "example",
    "examples",
    "example_stressors",
    "attractor",
    "attractors",
    "residues",
)

ROLE_PROVOKE = (
    "You are a {role}. Working only from what that person actually sees day to "
    "day, describe something that could happen in your part of this business "
    "that the current architecture has no answer for. Tell it as a short story "
    "about this specific system, not as a category of problem."
)


@dataclass(frozen=True)
class Lens:
    """One shard of the random simulation: a question, never an answer."""

    id: str
    provoke: str
    kind: str = "domain"


@dataclass(frozen=True)
class Profile:
    names: tuple[str, ...] = ()
    component_kinds: tuple[str, ...] = ()
    default_granularity: str = "component"
    flow_sources: tuple[str, ...] = ()
    flow_hint: str = ""
    lenses: tuple[Lens, ...] = ()
    actors: tuple[str, ...] = ()
    vocabulary: tuple[str, ...] = ()
    technical_markers: tuple[str, ...] = ()
    gates: Mapping[str, Any] = field(default_factory=dict)


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for value in values:
        text = str(value).strip()
        if text:
            seen.setdefault(text, None)
    return tuple(seen)


def _check_no_answers(raw: Mapping[str, Any], source: Path) -> None:
    def scan(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                lowered = str(key).strip().lower()
                if lowered in BANNED_PROFILE_KEYS:
                    raise ValueError(
                        f"{source}: profile key {path}{key!r} ships answers. "
                        "Profiles supply provocations only -- a shipped stressor "
                        "list makes every analysis produce the same rows."
                    )
                scan(value, f"{path}{key}.")
        elif isinstance(node, (list, tuple)):
            for item in node:
                scan(item, path)

    scan(raw, "")


def parse(raw: Mapping[str, Any], source: Path) -> tuple[Profile, tuple[str, ...]]:
    """Parse one profile file, returning it and the names it extends."""
    _check_no_answers(raw, source)

    components = raw.get("components") or {}
    flows = raw.get("flows") or {}
    actors = raw.get("actors") or {}

    lenses = tuple(
        Lens(
            id=str(entry["id"]).strip(),
            provoke=str(entry.get("provoke", "")).strip(),
            kind=str(entry.get("kind", "domain")).strip() or "domain",
        )
        for entry in (raw.get("lens") or [])
        if str(entry.get("id", "")).strip()
    )
    missing = [lens.id for lens in lenses if not lens.provoke]
    if missing:
        raise ValueError(f"{source}: lenses without a provocation: {', '.join(missing)}")

    profile = Profile(
        names=(str(raw.get("name", source.stem)),),
        component_kinds=_dedupe(components.get("kinds") or ()),
        default_granularity=str(components.get("default_granularity", "component")),
        flow_sources=_dedupe(flows.get("sources") or ()),
        flow_hint=str(flows.get("hint", "")).strip(),
        lenses=lenses,
        actors=_dedupe(actors.get("roles") or ()),
        vocabulary=_dedupe(raw.get("vocabulary") or ()),
        technical_markers=_dedupe((raw.get("gates") or {}).get("technical_markers") or ()),
        gates={
            k: v
            for k, v in (raw.get("gates") or {}).items()
            if k != "technical_markers"
        },
    )
    extends = tuple(str(e) for e in (raw.get("extends") or ()))
    return profile, extends


def merge(base: Profile, overlay: Profile) -> Profile:
    """Overlay wins scalars; collections accumulate; lenses dedupe by id."""
    lenses: dict[str, Lens] = {lens.id: lens for lens in base.lenses}
    for lens in overlay.lenses:
        lenses[lens.id] = lens
    return Profile(
        names=_dedupe((*base.names, *overlay.names)),
        component_kinds=_dedupe((*base.component_kinds, *overlay.component_kinds)),
        default_granularity=overlay.default_granularity or base.default_granularity,
        flow_sources=_dedupe((*base.flow_sources, *overlay.flow_sources)),
        flow_hint=overlay.flow_hint or base.flow_hint,
        lenses=tuple(lenses.values()),
        actors=_dedupe((*base.actors, *overlay.actors)),
        vocabulary=_dedupe((*base.vocabulary, *overlay.vocabulary)),
        technical_markers=_dedupe((*base.technical_markers, *overlay.technical_markers)),
        gates={**base.gates, **overlay.gates},
    )


def find(name: str, search_paths: Sequence[Path]) -> Path:
    """Later search paths win, so a private overlay can shadow a bundled one."""
    for directory in reversed(list(search_paths)):
        candidate = directory / f"{name}.toml"
        if candidate.exists():
            return candidate
    searched = ", ".join(str(p) for p in search_paths)
    raise FileNotFoundError(f"profile {name!r} not found in: {searched}")


def load(names: Sequence[str], search_paths: Sequence[Path]) -> Profile:
    """Load and merge *names*, resolving ``extends`` depth-first.

    A profile's own settings are applied after everything it extends, so an
    overlay always beats its base.
    """
    resolved = Profile()
    seen: set[str] = set()

    def visit(name: str, stack: tuple[str, ...]) -> None:
        nonlocal resolved
        if name in stack:
            raise ValueError(f"profile cycle: {' -> '.join((*stack, name))}")
        if name in seen:
            return
        path = find(name, search_paths)
        parsed, extends = parse(fs.read_toml(path), path)
        for parent in extends:
            visit(parent, (*stack, name))
        seen.add(name)
        resolved = merge(resolved, parsed)

    for name in names:
        visit(name, ())
    return resolved


def role_lenses(profile: Profile) -> tuple[Lens, ...]:
    """Persona shards derived from the profile's actors.

    Kept separate from declared lenses so a profile author lists roles once and
    gets one blind generator per role for free.
    """
    return tuple(
        Lens(
            id=f"role-{_slug(role)}",
            provoke=ROLE_PROVOKE.format(role=role),
            kind="role",
        )
        for role in profile.actors
    )


def all_lenses(profile: Profile) -> tuple[Lens, ...]:
    """Every shard of the simulation, in stable order."""
    return (*profile.lenses, *role_lenses(profile))


def _slug(value: str) -> str:
    out = "".join(ch if ch.isalnum() else "-" for ch in value.lower())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")
