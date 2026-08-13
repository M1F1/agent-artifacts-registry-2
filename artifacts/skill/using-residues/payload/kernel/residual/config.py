"""Repository-level configuration: capability bindings, runner, gate thresholds.

Config is human-authored, so it is TOML.  Anything the kernel writes back is
JSON, because :mod:`tomllib` reads but cannot write and hand-rolling a
serialiser to keep one file format uniform is not worth the code.

The capability table is the whole MCP story.  Steps ask for abstract
capabilities (``context.lineage``); this file says which concrete tools provide
them in *your* harness.  A new MCP server is a line here, never a code change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from . import fs, paths

CONFIG_NAME = "config.toml"

DEFAULT_GATES: Mapping[str, Any] = {
    # A stressor naming nothing from this system's vocabulary is generic by
    # construction (residuality-theory §stressors).
    "min_specificity": 1,
    # Lexical similarity above which two stressors are treated as the same row.
    # Calibrated against reworded pairs, which score around 0.77, versus
    # distinct stressors from the same lens, which score around 0.48. Raise it
    # if the gate is nagging; lower it if obvious restatements slip through.
    "duplicate_threshold": 0.68,
    # Similarity to the lens provocation above which the agent has restated the
    # prompt instead of thinking about the system.
    "paraphrase_threshold": 0.62,
    # Share of stressors allowed to be infrastructure-flavoured.  Heavily
    # technical lists are a warning sign (residuality-theory §technical-skew).
    "technical_quota": 0.15,
    "min_records_per_shard": 8,
    "max_attempts": 3,
    "claim_ttl_seconds": 1800,
}

DEFAULT_RUNNER: Mapping[str, str] = {
    # Command used by the restart loop.  {prompt_file} is substituted with the
    # path to the rendered unit prompt.
    "cmd": "",
    "prompt_file": ".residuality/unit.md",
}


@dataclass(frozen=True)
class Config:
    root: Path
    profiles: tuple[str, ...] = ()
    capabilities: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    runner: Mapping[str, str] = field(default_factory=lambda: dict(DEFAULT_RUNNER))
    gates: Mapping[str, Any] = field(default_factory=lambda: dict(DEFAULT_GATES))
    steps: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)

    @property
    def profile_search_paths(self) -> tuple[Path, ...]:
        """Bundled profiles first, then workplace-private ones, which win.

        Company specifics -- real team names, regulators, internal systems --
        belong in ``.residuality/profiles`` and never in the shared framework.
        """
        return (paths.bundled_profiles(), self.root / "profiles")


def find_root(start: Path | None = None) -> Path:
    """Nearest ``.residuality`` directory walking up from *start*, else cwd."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        marker = candidate / ".residuality"
        if marker.is_dir():
            return marker
    return here / ".residuality"


def load(root: Path | None = None) -> Config:
    base = root or find_root()
    path = base / CONFIG_NAME
    raw: Mapping[str, Any] = fs.read_toml(path) if path.exists() else {}

    capabilities = {
        str(k): tuple(str(v) for v in vals)
        for k, vals in (raw.get("capabilities") or {}).items()
    }
    profiles = raw.get("profiles") or ([raw["profile"]] if raw.get("profile") else [])

    return Config(
        root=base,
        profiles=tuple(str(p) for p in profiles),
        capabilities=capabilities,
        runner={**DEFAULT_RUNNER, **(raw.get("runner") or {})},
        gates={**DEFAULT_GATES, **(raw.get("gates") or {})},
        steps={str(k): dict(v) for k, v in (raw.get("step") or {}).items()},
    )


def gate(config: Config, name: str, step_id: str = "") -> Any:
    """Gate value for *step_id*, falling back to the global then the default."""
    step_gates = (config.steps.get(step_id) or {}).get("gates") or {}
    if name in step_gates:
        return step_gates[name]
    return config.gates.get(name, DEFAULT_GATES.get(name))


def tools_for(config: Config, capability: str) -> tuple[str, ...]:
    return tuple(config.capabilities.get(capability, ()))
