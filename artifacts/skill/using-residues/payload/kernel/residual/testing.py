"""Running tests that live inside the skills.

``unittest discover`` will not descend into ``skills/residual-06-matrix``: the
directory name is not a Python identifier, so it is not importable as a
package, and discovery skips it. Rather than bend the layout to suit the test
runner -- renaming directories a human reads, or scattering ``__init__.py``
files through the skills -- the loader here walks the tree and loads each test
module by path, the same way :mod:`residual.registry` loads the steps.

The result is that a skill owns its tests: ``skills/<skill>/tests/test_*.py``
runs with the skill, on its own, and as part of everything.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Iterable, Sequence

from . import paths

TEST_GLOB = "test_*.py"


def _load(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load test module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def suite_for(paths: Iterable[Path]) -> unittest.TestSuite:
    """A suite over every ``test_*.py`` under each of *paths*."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for directory in paths:
        for path in sorted(directory.rglob(TEST_GLOB)):
            name = f"residual._tests.{path.parent.parent.name}.{path.stem}"
            suite.addTests(loader.loadTestsFromModule(_load(path, name)))
    return suite


def run(paths: Sequence[Path], verbosity: int = 1) -> bool:
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite_for(paths))
    return result.wasSuccessful()


def run_skill(skill_dir: Path, verbosity: int = 2) -> bool:
    tests = Path(skill_dir) / "tests"
    if not tests.is_dir():
        print(f"{skill_dir.name}: no tests/ directory")
        return True
    return run([tests], verbosity=verbosity)


def all_test_dirs() -> tuple[Path, ...]:
    """The kernel's own tests plus every skill's, in a stable order.

    Both are found from where the kernel actually is, so this works from a
    checkout and from an installed skills directory alike.
    """
    found = [paths.kernel_dir() / "tests"]
    skills = paths.skills_root()
    if skills.is_dir():
        found += [d / "tests" for d in sorted(skills.iterdir()) if (d / "tests").is_dir()]
    return tuple(dict.fromkeys(d for d in found if d.is_dir()))
