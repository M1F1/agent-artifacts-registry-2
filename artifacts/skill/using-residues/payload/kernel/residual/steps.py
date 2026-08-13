"""How a step splits into claimable work units.

``shard_by`` is the whole parallel/sequential story. A step declares how it
divides, and the same declaration drives three execution modes: one subagent
per shard, one restarted process per shard, or one agent walking the shards in
sequence. Nothing else in the kernel knows which mode is in play.

The steps themselves are no longer listed here. Each one lives in its own skill
under ``skills/``, declaring its ``StepSpec`` beside the prose an agent reads
and the code that compiles and gates its output; :mod:`residual.registry` finds
them. This module keeps only what is true of *every* step: how it shards.
"""

from __future__ import annotations

from typing import Any

from . import fs
from . import profiles as profiles_mod
from . import registry
from .config import Config
from .model import StepSpec, Unit

UNIT_SEP = "--"

#: Fields carried into a batch unit's payload, so the prompt can show the rows
#: without the agent going back to the register and reading its neighbours.
BATCH_PREVIEW_FIELDS: tuple[str, ...] = (
    "id",
    "lens",
    "stressor",
    "detection",
    "attractor",
    "business_reaction",
    "technical_change",
)


def __getattr__(name: str) -> Any:
    """``steps.STEPS`` still works; it is now resolved from the skills.

    Lazy on purpose: importing this module must not go and execute nine skill
    modules, or a syntax error in one step would break every command.
    """
    if name == "STEPS":
        return registry.specs()
    raise AttributeError(name)


def by_id(step_id: str) -> StepSpec:
    return registry.spec(step_id)


def step_ids() -> tuple[str, ...]:
    return tuple(spec.id for spec in registry.specs())


def unit_id(step_id: str, shard: str) -> str:
    return f"{step_id}{UNIT_SEP}{shard}"


def step_of(unit_id_value: str) -> str:
    return unit_id_value.split(UNIT_SEP, 1)[0]


def granularity(spec: StepSpec, config: Config) -> str:
    """Effective sharding, letting config override the step's default.

    This is the knob for how often context gets cleared: ``lens`` keeps a whole
    lens in one context, ``batch:1`` clears it after every single record.
    """
    override = (config.steps.get(spec.id) or {}).get("unit")
    return str(override) if override else spec.shard_by


def _batch_size(mode: str, spec: StepSpec) -> int:
    _, _, raw = mode.partition(":")
    try:
        size = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"{spec.id}: batch sharding needs a size, e.g. 'batch:20', got {mode!r}"
        ) from exc
    if size < 1:
        raise ValueError(f"{spec.id}: batch size must be at least 1, got {size}")
    return size


def _batch_units(spec: StepSpec, config: Config, run_dir) -> tuple[Unit, ...]:
    if not spec.batch_source:
        raise ValueError(f"{spec.id}: batch sharding needs a batch_source")
    source = run_dir / spec.batch_source
    rows = fs.read_csv(source)
    if not rows:
        raise ValueError(
            f"{spec.id}: {spec.batch_source} is empty or missing, so there is "
            "nothing to batch. Run the step that produces it first."
        )

    size = _batch_size(granularity(spec, config), spec)
    units: list[Unit] = []
    for index in range(0, len(rows), size):
        chunk = rows[index : index + size]
        shard = f"b{index // size + 1:03d}"
        units.append(
            Unit(
                id=unit_id(spec.id, shard),
                step=spec.id,
                shard=shard,
                payload={
                    "ids": [row.get("id", "") for row in chunk],
                    "rows": [
                        {f: row.get(f, "") for f in BATCH_PREVIEW_FIELDS if row.get(f)}
                        for row in chunk
                    ],
                },
            )
        )
    return tuple(units)


def expand(
    spec: StepSpec,
    profile: profiles_mod.Profile,
    config: Config,
    run_dir=None,
) -> tuple[Unit, ...]:
    """Split *spec* into independently claimable work units."""
    mode = granularity(spec, config)

    if mode == "single":
        return (Unit(id=unit_id(spec.id, "all"), step=spec.id, shard="all", payload={}),)

    if mode == "lens":
        lenses = profiles_mod.all_lenses(profile)
        if not lenses:
            raise ValueError(
                f"{spec.id}: the active profile declares no lenses, so there is "
                "nothing to shard. Check `profiles` in .residuality/config.toml."
            )
        return tuple(
            Unit(
                id=unit_id(spec.id, lens.id),
                step=spec.id,
                shard=lens.id,
                payload={"lens": lens.id, "kind": lens.kind, "provoke": lens.provoke},
            )
            for lens in lenses
        )

    if mode.startswith("batch:"):
        if run_dir is None:
            raise ValueError(f"{spec.id}: batch sharding needs the run directory")
        return _batch_units(spec, config, run_dir)

    raise ValueError(
        f"{spec.id}: unsupported sharding {mode!r}. "
        "Supported: 'single', 'lens', 'batch:N'."
    )
