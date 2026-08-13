"""Deterministic, dependency-free rendering of run artifacts to HTML."""

from .report import simple_report, stressor_report

__all__ = ["simple_report", "stressor_report"]
