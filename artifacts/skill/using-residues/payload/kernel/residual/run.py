"""Run directories: where a residuality analysis keeps its state.

State lives in files, never in an agent's context.  That is what lets a session
die mid-run, or the whole harness change, without losing the analysis -- and it
is the only reason the same run can be driven by parallel subagents in one
harness and a restart loop in another.

The kernel never reads the clock.  Ordering comes from sorted filenames and
staleness from file mtime, so identical inputs always produce identical
artifacts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from . import fs
from .model import SCHEMA_VERSION, StepSpec, is_blind

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")

META_NAME = "run.json"


@dataclass(frozen=True)
class RunContext:
    """Everything a command needs to locate and label artifacts."""

    root: Path
    slug: str
    mode: str = "in-session"
    harness: str = ""
    model: str = ""
    profiles: tuple[str, ...] = ()

    @property
    def dir(self) -> Path:
        return self.root / "runs" / self.slug

    @property
    def blind(self) -> bool:
        return is_blind(self.mode)


def slugify(name: str) -> str:
    return _SLUG_STRIP.sub("-", name.strip().lower()).strip("-") or "run"


def meta_path(ctx: RunContext) -> Path:
    return ctx.dir / META_NAME


def to_meta(ctx: RunContext) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "slug": ctx.slug,
        "mode": ctx.mode,
        "blind": ctx.blind,
        "harness": ctx.harness,
        "model": ctx.model,
        "profiles": list(ctx.profiles),
    }


def from_meta(root: Path, meta: Mapping[str, Any]) -> RunContext:
    return RunContext(
        root=root,
        slug=str(meta.get("slug", "run")),
        mode=str(meta.get("mode", "in-session")),
        harness=str(meta.get("harness", "")),
        model=str(meta.get("model", "")),
        profiles=tuple(str(p) for p in meta.get("profiles") or ()),
    )


def create(ctx: RunContext) -> RunContext:
    fs.ensure_dir(ctx.dir)
    fs.write_json(meta_path(ctx), to_meta(ctx))
    return ctx


def load(root: Path, slug: str) -> RunContext:
    ctx = RunContext(root=root, slug=slug)
    path = meta_path(ctx)
    if not path.exists():
        raise FileNotFoundError(
            f"no run at {ctx.dir} -- create one with `residual init <name>`"
        )
    return from_meta(root, fs.read_json(path))


def update(ctx: RunContext, **changes: Any) -> RunContext:
    merged = {**to_meta(ctx), **changes}
    updated = from_meta(ctx.root, merged)
    fs.write_json(meta_path(updated), to_meta(updated))
    return updated


def latest_slug(root: Path) -> str | None:
    """Most recently modified run, so commands can default to `the run`."""
    runs = root / "runs"
    if not runs.is_dir():
        return None
    candidates = [d for d in runs.iterdir() if (d / META_NAME).exists()]
    if not candidates:
        return None
    return max(candidates, key=lambda d: (d / META_NAME).stat().st_mtime).name


# --------------------------------------------------------------------------
# artifact paths
# --------------------------------------------------------------------------


def step_dir(ctx: RunContext, spec: StepSpec) -> Path:
    return ctx.dir / spec.id


def shard_path(ctx: RunContext, spec: StepSpec, shard: str) -> Path:
    return ctx.dir / spec.output_template.format(shard=shard)


def raw_dir(ctx: RunContext, spec: StepSpec) -> Path:
    """Directory holding shard writes.

    Derived from the output template so that a step which changes its layout
    does not need a second declaration to stay consistent.
    """
    return (ctx.dir / spec.output_template.format(shard="_")).parent


def compiled_path(ctx: RunContext, spec: StepSpec) -> Path:
    return ctx.dir / spec.compiled


def report_path(ctx: RunContext, spec: StepSpec) -> Path:
    return ctx.dir / "reports" / f"{spec.id}.html"


def resolve_input(ctx: RunContext, relative: str) -> Path:
    return ctx.dir / relative
