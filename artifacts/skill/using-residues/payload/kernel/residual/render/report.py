"""Step reports: what the register looks like and where the gates bit.

The report is a provocation for a conversation, not a verdict. The book is
explicit that the value of the matrices and lists is the discussion they
trigger (residuality-theory §the-artifacts), so numbers here are framed to point at what to
argue about rather than to certify anything as finished.

What a report *shows* is specific to its step, so most of them live in their
own skill beside the step that produces the artifact -- the contagion heatmap
with ``06-matrix``, the Ri tiles with ``09-ri``. Here are the pieces every
report reuses: the gate-findings table, the fallback report for steps whose
output is prose or a plain list, and the stressor register report that both
``03-stressors`` and ``08-holdout`` render.
"""

from __future__ import annotations

from html import escape
from typing import Sequence

from .. import registry
from ..model import GateResult, StepSpec, Stressor
from ..profiles import Profile
from ..run import RunContext
from . import page
from .svg import Bar, bar_chart

SEVERITY_TONE = {"error": "err", "warning": "warn"}


def escape_text(value: str) -> str:
    return escape(value)


def issue_rows(gate: GateResult) -> list[tuple[str, str, str, str]]:
    order = {"error": 0, "warning": 1}
    ranked = sorted(gate.issues, key=lambda i: (order.get(i.severity, 2), i.code, i.where))
    return [(i.severity, i.code, i.where or "—", i.detail) for i in ranked]


def gate_section(gate: GateResult) -> list[str]:
    """The findings table, or nothing at all when the gate had nothing to say."""
    issues = issue_rows(gate)
    if not issues:
        return []
    rows = [
        (
            page.Raw(f'<span class="rz-pill {SEVERITY_TONE.get(sev, "")}">{sev}</span>'),
            code,
            where,
            detail,
        )
        for sev, code, where, detail in issues
    ]
    return [
        page.section(
            "Gate findings",
            page.panel(page.table(("Severity", "Check", "Where", "Detail"), rows)),
        )
    ]


def document(ctx: RunContext, spec: StepSpec, sections: Sequence[str]) -> str:
    """The page shell, with the run's identity in the subtitle."""
    return page.document(
        f"Residuality · {spec.id}", f"{spec.title} — run “{ctx.slug}”", list(sections)
    )


def _lens_bars(gate: GateResult) -> tuple[Bar, ...]:
    per_lens = gate.stats.get("per_lens") or {}
    return tuple(
        Bar(label=lens, value=float(count), note=str(count))
        for lens, count in sorted(per_lens.items(), key=lambda kv: (-kv[1], kv[0]))
    )


def _summary_tiles(gate: GateResult) -> Sequence[tuple[str, str, str]]:
    stats = gate.stats
    records = int(stats.get("records", 0))
    blind_share = float(stats.get("blind_share", 0.0))
    technical = float(stats.get("technical_share", 0.0))
    duplicates = int(stats.get("duplicate_pairs", 0))
    return [
        ("Stressors", str(records), f"{stats.get('lenses', 0)} lenses"),
        (
            "Blind",
            f"{blind_share:.0%}",
            "generated in an uncontaminated context",
        ),
        (
            "Technical share",
            f"{technical:.0%}",
            "high means the walk never left the machine room",
        ),
        (
            "Duplicate pairs",
            str(duplicates),
            "lexical only — a lower bound",
        ),
        (
            "Gate",
            "pass" if gate.ok else "fail",
            f"{len(gate.errors)} errors, {len(gate.warnings)} warnings",
        ),
    ]


def stressor_report(
    ctx: RunContext,
    spec: StepSpec,
    stressors: Sequence[Stressor],
    gate: GateResult,
    profile: Profile,
) -> str:
    """The register, its coverage by lens, and what the gate found.

    Shared by the training and holdout steps: the same table, judged the same
    way, so the two are readable side by side.
    """
    sections: list[str] = [page.tiles(_summary_tiles(gate))]

    sections.append(
        page.section(
            "Coverage by lens",
            page.panel(
                bar_chart(_lens_bars(gate), "Stressors per lens")
                + '<p class="rz-note">A lens with far fewer rows than its '
                "neighbours usually means the shard ran thin, not that the lens "
                "had nothing to say. An empty one is worth re-running before "
                "reading anything else here.</p>"
            ),
        )
    )

    sections += gate_section(gate)

    register_rows = [
        (
            s.id,
            s.lens,
            s.stressor,
            s.detection,
            s.attractor,
            s.business_reaction,
            s.technical_change or "—",
        )
        for s in stressors
    ]
    sections.append(
        page.section(
            "Register",
            page.panel(
                page.table(
                    (
                        "id",
                        "Lens",
                        "Stressor",
                        "Detection",
                        "Attractor",
                        "Business reaction",
                        "Technical change",
                    ),
                    register_rows,
                    table_id="rz-register",
                    filterable=True,
                )
            ),
        )
    )

    subtitle = (
        f"{spec.title} — run “{ctx.slug}”, mode {ctx.mode}"
        + (f", profile {', '.join(profile.names)}" if profile.names else "")
    )
    return page.document(f"Residuality · {spec.id}", subtitle, sections)


def simple_report(ctx: RunContext, spec: StepSpec, gate: GateResult) -> str:
    """Fallback for steps whose output speaks for itself: stats and findings."""
    stats_rows = [(k, str(v)) for k, v in sorted(gate.stats.items())]
    sections = [page.panel(page.table(("Statistic", "Value"), stats_rows))]
    sections += gate_section(gate)
    return document(ctx, spec, sections)


def build(ctx: RunContext, spec: StepSpec, gate: GateResult, profile: Profile) -> str:
    """One entry point for the CLI; the step's skill decides what it renders."""
    render = registry.hook(spec.id, "report")
    if render is None:
        return simple_report(ctx, spec, gate)
    return render(ctx, spec, gate, profile)
