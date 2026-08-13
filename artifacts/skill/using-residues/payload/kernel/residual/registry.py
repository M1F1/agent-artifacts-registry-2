"""Finding the steps, which live inside the skills rather than in the kernel.

A step is not a table entry here: it is a directory beside this skill holding
the prose an agent reads (``SKILL.md``), the code that compiles and gates its
output (``step.py`` and whatever it imports beside it), a runner
(``scripts/run.py``) and its own tests. This module is the only thing that
knows how to find and load them; :mod:`residual.paths` knows where to look.

The split that keeps this honest: **logic used by exactly one step lives in
that step's skill; logic shared by two or more lives in the kernel.** So the
contagion matrix belongs to ``06-matrix`` and the Ri arithmetic to ``09-ri``,
while shard reading, the stressor gate primitives and the HTML page shell stay
here, where both stressor steps can reach them.

Loading is by path, not by import name, because ``residual-03-stressors`` is a
directory name a human can read and not a Python identifier. Modules are cached
under a private name so two skills may each have a ``report.py`` without
colliding.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from . import paths
from .model import StepSpec

#: Point this at another directory to run a modified or extended pipeline
#: without touching the kernel.
SKILLS_ENV = paths.SKILLS_ENV

STEP_MODULE = "step.py"

_MODULE_PREFIX = "residual._skills"

_cache: dict[str, ModuleType] | None = None


def skills_root() -> Path:
    return paths.skills_root()


def _load(path: Path, name: str) -> ModuleType:
    existing = sys.modules.get(name)
    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _slug(directory: Path) -> str:
    return directory.name.replace("-", "_")


def _discover() -> dict[str, ModuleType]:
    root = skills_root()
    if not root.is_dir():
        raise FileNotFoundError(
            f"no skills directory at {root}. Every step lives in one; set "
            f"{SKILLS_ENV} if yours is somewhere else."
        )

    found: dict[str, ModuleType] = {}
    for directory in sorted(p for p in root.iterdir() if p.is_dir()):
        step_file = directory / STEP_MODULE
        if not step_file.exists():
            continue  # prose-only skills: the harness adapters, the overview

        module = _load(step_file, f"{_MODULE_PREFIX}.{_slug(directory)}.step")
        spec = getattr(module, "SPEC", None)
        if not isinstance(spec, StepSpec):
            raise ValueError(
                f"{step_file} defines no SPEC. A step skill must export a "
                "StepSpec named SPEC."
            )
        if spec.id in found:
            raise ValueError(f"two skills claim step id {spec.id!r}")
        found[spec.id] = module
    if not found:
        raise ValueError(f"no step skills under {root}")
    return found


def modules() -> tuple[ModuleType, ...]:
    """Every step module, in pipeline order (their directories sort by number)."""
    global _cache
    if _cache is None:
        _cache = _discover()
    return tuple(_cache.values())


def reload() -> None:
    """Drop the cache. For tests that point :data:`SKILLS_ENV` somewhere else."""
    global _cache
    if _cache is not None:
        for module in _cache.values():
            sys.modules.pop(module.__name__, None)
    _cache = None


def module(step_id: str) -> ModuleType:
    modules()
    assert _cache is not None
    try:
        return _cache[step_id]
    except KeyError as exc:
        known = ", ".join(_cache)
        raise KeyError(f"unknown step {step_id!r}; known steps: {known}") from exc


def specs() -> tuple[StepSpec, ...]:
    return tuple(m.SPEC for m in modules())


def spec(step_id: str) -> StepSpec:
    return module(step_id).SPEC


def hook(step_id: str, name: str, default: Any = None) -> Any:
    """A step's optional contribution: ``gate``, ``report``, ``prompt_context``...

    Steps declare only what they actually change. A step with nothing to say
    about, say, its report gets the kernel's fallback rather than a stub.
    """
    return getattr(module(step_id), name, default)


def call(step_id: str, name: str, *args: Any, **kwargs: Any) -> Any:
    fn: Callable[..., Any] | None = hook(step_id, name)
    if fn is None:
        raise ValueError(f"{step_id}: skill defines no {name}()")
    return fn(*args, **kwargs)


# --------------------------------------------------------------------------
# a skill's own files
# --------------------------------------------------------------------------


def skill_dir(step_id: str) -> Path:
    return Path(os.path.abspath(module(step_id).__file__)).parent


def step_id_at(skill_dir: str | Path) -> str:
    """Which step a skill directory implements, for its own runner script."""
    wanted = Path(os.path.abspath(skill_dir))
    for step_module in modules():
        if Path(os.path.abspath(step_module.__file__)).parent == wanted:
            return step_module.SPEC.id
    raise ValueError(f"{wanted} holds no step module ({STEP_MODULE})")


def sibling(step_file: str | Path, name: str) -> ModuleType:
    """Import ``<name>.py`` from beside a step module.

    Used by a skill to reach its own helpers -- ``matrix.py``, ``ri.py``,
    ``report.py`` -- without those names becoming global and colliding with
    another skill's file of the same name.
    """
    directory = Path(os.path.abspath(step_file)).parent
    return _load(directory / f"{name}.py", f"{_MODULE_PREFIX}.{_slug(directory)}.{name}")


def sibling_of(step_id: str, name: str) -> ModuleType:
    """The same, addressed by step id. This is how a skill's tests import it."""
    return sibling(module(step_id).__file__, name)


def skill_dirs() -> tuple[Path, ...]:
    """Every skill directory, step or not -- prose-only skills included."""
    root = skills_root()
    if not root.is_dir():
        return ()
    return tuple(
        p for p in sorted(root.iterdir()) if p.is_dir() and (p / "SKILL.md").exists()
    )
