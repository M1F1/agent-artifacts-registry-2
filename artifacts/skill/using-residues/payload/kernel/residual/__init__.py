"""Residuality analysis kernel: stdlib only, harness agnostic.

It ships inside the ``using-residues`` skill rather than beside it, so that
fetching skills gives you something that runs. Every stage skill finds it at
``../using-residues/kernel``; :mod:`residual.paths` is where that assumption
lives, and ``residual where`` prints what it resolved to.

The design in one line: **state lives in files, never in an agent's context.**
A run is a directory; any agent in any harness can open it, see what is done,
and continue. That is what makes parallel subagents, a restart loop and a
single sequential session interchangeable ways of driving the same analysis.

Everything the kernel decides is deterministic -- ordering from sorted
filenames, identifiers assigned at compile time, gates computed by code. The
agents supply imagination; the kernel supplies the standard.
"""

from .model import SCHEMA_VERSION

__all__ = ["SCHEMA_VERSION"]
