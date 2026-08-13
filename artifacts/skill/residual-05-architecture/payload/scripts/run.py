#!/usr/bin/env python3
"""Run this step on its own: plan, next, done, compile, gate, report, test.

    python skills/residual-05-architecture/scripts/run.py gate

The step is implied by where this file lives, so a copied skill directory needs
no edit. Everything goes through the same kernel as `residual <command> <step>`;
the only difference is that you cannot address another step by accident.
"""

import os
import sys
from pathlib import Path

HERE = Path(os.path.abspath(__file__)).parent


def kernel_paths():
    """Where the kernel might be, most explicit first.

    This runs *before* anything is importable, so it cannot ask the kernel
    where the kernel is. The sibling case is the normal one: skills installed
    together land in one directory, and `using-residues` carries the kernel.
    """
    override = os.environ.get("RESIDUAL_KERNEL")
    if override:
        yield Path(override).expanduser()
    for base in (HERE.parent, Path(__file__).parent.parent):
        yield base.parent / "using-residues" / "kernel"


def bootstrap() -> None:
    for candidate in kernel_paths():
        if (candidate / "residual" / "__init__.py").exists():
            sys.path.insert(0, str(candidate))
            return
    try:
        import residual  # noqa: F401  (pip-installed kernel)
    except ImportError:
        sys.exit(
            "cannot find the residual kernel. It ships inside the "
            "`using-residues` skill, which this skill expects beside it:\n"
            f"  looked in: {', '.join(str(p) for p in kernel_paths())}\n"
            "Install that skill too, or set RESIDUAL_KERNEL to its kernel/ directory."
        )


bootstrap()

from residual import stepcli  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(stepcli.main(__file__))
