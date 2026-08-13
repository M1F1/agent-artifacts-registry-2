"""The work queue: one claimable unit per file, state encoded by directory.

Claiming is an ``os.replace`` from ``pending/`` into ``claimed/``, which is
atomic.  If two workers race for the same unit, exactly one rename succeeds and
the loser gets ``FileNotFoundError`` and moves on.  That is the entire
concurrency story -- no locks, no daemon, no database -- and it is what lets
parallel subagents, a restart loop, and a single in-session agent share one
implementation.

It also makes resume free: the queue *is* the progress record, so a killed
session loses at most one unit.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable, Iterator

from . import fs
from .model import Unit, unit_from_mapping, unit_to_mapping
from .run import RunContext

STATES: tuple[str, ...] = ("pending", "claimed", "done", "failed")


def queue_dir(ctx: RunContext, state: str = "") -> Path:
    base = ctx.dir / "queue"
    return base / state if state else base


def unit_path(ctx: RunContext, state: str, unit_id: str) -> Path:
    return queue_dir(ctx, state) / f"{unit_id}.json"


def _write_unit(path: Path, unit: Unit) -> Path:
    return fs.write_json(path, unit_to_mapping(unit))


def _read_unit(path: Path) -> Unit:
    return unit_from_mapping(fs.read_json(path))


def plan(ctx: RunContext, units: Iterable[Unit], replace: bool = False) -> tuple[Unit, ...]:
    """Write *units* into ``pending/``.

    Existing units are left alone unless *replace* is set, so re-planning a step
    after adding a lens adds the new work without discarding finished shards.
    """
    for state in STATES:
        fs.ensure_dir(queue_dir(ctx, state))

    written: list[Unit] = []
    for unit in units:
        already = any(unit_path(ctx, state, unit.id).exists() for state in STATES)
        if already and not replace:
            continue
        if already and replace:
            for state in STATES:
                path = unit_path(ctx, state, unit.id)
                if path.exists():
                    path.unlink()
        _write_unit(unit_path(ctx, "pending", unit.id), unit)
        written.append(unit)
    return tuple(written)


def reclaim_stale(ctx: RunContext, ttl_seconds: int) -> tuple[str, ...]:
    """Return units abandoned mid-flight to ``pending``, counting the attempt.

    Without this a crashed loop iteration would wedge its unit in ``claimed/``
    forever and the step would never reach its gate.
    """
    claimed = queue_dir(ctx, "claimed")
    if not claimed.is_dir():
        return ()
    cutoff = time.time() - max(ttl_seconds, 0)
    reclaimed: list[str] = []
    for path in fs.iter_files(claimed, ".json"):
        if path.stat().st_mtime > cutoff:
            continue
        unit = _read_unit(path)
        bumped = Unit(
            id=unit.id,
            step=unit.step,
            shard=unit.shard,
            payload=unit.payload,
            attempts=unit.attempts + 1,
        )
        _write_unit(unit_path(ctx, "pending", unit.id), bumped)
        path.unlink()
        reclaimed.append(unit.id)
    return tuple(reclaimed)


def claim(ctx: RunContext, step: str = "", ttl_seconds: int = 1800) -> Unit | None:
    """Atomically take the next pending unit, optionally filtered to *step*.

    Returns ``None`` when nothing is left, which is what terminates the restart
    loop -- the loop stops because the work is done, not on a token budget.
    """
    reclaim_stale(ctx, ttl_seconds)
    for path in fs.iter_files(queue_dir(ctx, "pending"), ".json"):
        if step and not path.name.startswith(f"{step}--"):
            continue
        target = unit_path(ctx, "claimed", path.stem)
        try:
            fs.move(path, target)
        except (FileNotFoundError, OSError):
            continue  # another worker won the race; try the next one
        return _read_unit(target)
    return None


def complete(ctx: RunContext, unit_id: str) -> Unit:
    source = unit_path(ctx, "claimed", unit_id)
    if not source.exists():
        raise FileNotFoundError(f"unit {unit_id!r} is not claimed")
    unit = _read_unit(source)
    fs.move(source, unit_path(ctx, "done", unit_id))
    return unit


def fail(ctx: RunContext, unit_id: str, reason: str, max_attempts: int = 3) -> tuple[Unit, str]:
    """Requeue a failed unit, or park it in ``failed/`` once attempts run out."""
    source = unit_path(ctx, "claimed", unit_id)
    if not source.exists():
        source = unit_path(ctx, "pending", unit_id)
    if not source.exists():
        raise FileNotFoundError(f"unit {unit_id!r} not found in the queue")

    unit = _read_unit(source)
    bumped = Unit(
        id=unit.id,
        step=unit.step,
        shard=unit.shard,
        payload={**dict(unit.payload), "last_failure": reason},
        attempts=unit.attempts + 1,
    )
    state = "pending" if bumped.attempts < max_attempts else "failed"
    _write_unit(unit_path(ctx, state, unit_id), bumped)
    source.unlink()
    return bumped, state


def iter_units(ctx: RunContext, state: str) -> Iterator[Unit]:
    for path in fs.iter_files(queue_dir(ctx, state), ".json"):
        yield _read_unit(path)


def counts(ctx: RunContext, step: str = "") -> dict[str, int]:
    def matching(state: str) -> int:
        return sum(
            1
            for path in fs.iter_files(queue_dir(ctx, state), ".json")
            if not step or path.name.startswith(f"{step}--")
        )

    return {state: matching(state) for state in STATES}


def is_drained(ctx: RunContext, step: str = "") -> bool:
    tally = counts(ctx, step)
    return tally["pending"] == 0 and tally["claimed"] == 0
