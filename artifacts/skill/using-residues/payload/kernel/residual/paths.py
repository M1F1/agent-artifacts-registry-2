"""Where the kernel is, and where the skills are, wherever this was installed.

The kernel ships *inside* a skill — ``using-residues/kernel/`` — so that fetching
a skill gives you something that runs, rather than something that needs a repo
checked out somewhere else. Every other skill in the pack is that skill's
sibling, both in this repository and after an install:

    <skills root>/
      using-residues/kernel/residual/     <- this package
      residual-06-matrix/step.py          <- finds the kernel at ../using-residues

That single invariant is what makes the layout work in three places at once: a
git checkout, ``.claude/skills/`` (or ``.tabnine/agent/skills/``) after an
``aart install``, and a plain ``pip install`` of the kernel alone.

Resolution order, most explicit first:

1. ``RESIDUAL_SKILLS`` -- an explicit skills directory;
2. the sibling layout above, derived from this file's location;
3. ``./skills`` under the current working directory, for a pip-installed CLI
   pointed at a checkout.

Nothing here reads the network or the clock, and nothing is cached: a test that
moves the skills directory gets the new answer.
"""

from __future__ import annotations

import os
from pathlib import Path

SKILLS_ENV = "RESIDUAL_SKILLS"

#: This package's directory: ``.../using-residues/kernel/residual``. Preserve
#: the lexical installed path so an AART-managed symlink still has the other
#: installed skills as siblings; resolving it would jump into the object store.
PACKAGE_DIR = Path(os.path.abspath(__file__)).parent

#: Data that travels with the kernel -- the bundled profiles.
DATA_DIR = PACKAGE_DIR / "data"


def kernel_dir() -> Path:
    """The ``kernel/`` directory holding this package and its tests."""
    return PACKAGE_DIR.parent


def skill_root() -> Path:
    """The ``using-residues`` skill directory, if the kernel still lives in one."""
    return kernel_dir().parent


def _sibling_skills() -> Path | None:
    """``<skills root>`` derived from the sibling layout, when it holds."""
    candidate = skill_root().parent
    if (candidate / skill_root().name).is_dir() and kernel_dir().name == "kernel":
        return candidate
    return None


def skills_root() -> Path:
    """The directory holding every skill, this one included."""
    override = os.environ.get(SKILLS_ENV)
    if override:
        return Path(override).expanduser().resolve()

    sibling = _sibling_skills()
    if sibling is not None:
        return sibling

    # A pip-installed kernel has no skills beside it; fall back to the project
    # being worked on, and let the registry produce the error if it is empty.
    return (Path.cwd() / "skills").resolve()


def bundled_profiles() -> Path:
    """Profiles shipped with the kernel, overridable per workplace in a run root."""
    return DATA_DIR


def describe() -> tuple[tuple[str, str], ...]:
    """(label, path) pairs for ``residual where`` and error messages."""
    return (
        ("kernel", str(kernel_dir())),
        ("skills", str(skills_root())),
        ("profiles", str(bundled_profiles())),
        ("skills source", SKILLS_ENV if os.environ.get(SKILLS_ENV) else "layout"),
    )
