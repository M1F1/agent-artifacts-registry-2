"""The Ri report: the number, its verdict, and every judgment behind it.

The per-stressor table is the point. A single Ri figure invites treating the
analysis as graded; the rows show which unseen stressors the residual
architecture actually absorbed, and by what mechanism.
"""

from __future__ import annotations

from residual import merge, registry
from residual.model import GateResult, StepSpec
from residual.render import page
from residual.render import report as report_mod
from residual.render.svg import Bar, bar_chart
from residual.run import RunContext

ri = registry.sibling(__file__, "ri")


def _judgment_rows(ctx: RunContext) -> list[tuple[str, str, str, str]]:
    by_stressor: dict[str, dict[str, object]] = {}
    for judgment in merge.load_judgments(ctx):
        try:
            architecture = ri.architecture_of(ctx.slug, judgment.arch)
        except ValueError:
            continue
        by_stressor.setdefault(judgment.stressor_id, {})[architecture] = judgment

    rows: list[tuple[str, str, str, str]] = []
    for stressor_id in sorted(by_stressor):
        slot = by_stressor[stressor_id]
        naive = slot.get("naive")
        residual = slot.get("residual")
        rows.append(
            (
                stressor_id,
                "survives" if getattr(naive, "survives", False) else "—",
                "survives" if getattr(residual, "survives", False) else "—",
                getattr(residual, "mechanism", "") or "—",
            )
        )
    return rows


def build(ctx: RunContext, spec: StepSpec, gate: GateResult) -> str:
    step = registry.module("09-ri")
    result = step.score(ctx)

    tiles = [
        ("Ri", f"{result.ri:+.2f}", "(Y − X) / S"),
        ("S", str(result.stressors), "unseen stressors judged for both"),
        ("X", str(result.naive_survivals), "naïve architecture survives"),
        ("Y", str(result.residual_survivals), "residual architecture survives"),
        (
            "Blind",
            "yes" if result.blind else "no",
            "judge and holdout in cold contexts",
        ),
    ]

    bars = (
        Bar(
            label="naïve (X)",
            value=float(result.naive_survivals),
            note=str(result.naive_survivals),
        ),
        Bar(
            label="residual (Y)",
            value=float(result.residual_survivals),
            note=str(result.residual_survivals),
        ),
    )

    sections = [
        page.tiles(tiles),
        page.section(
            "Verdict",
            page.panel(
                f'<p class="rz-verdict">{report_mod.escape_text(ri.interpret(result))}</p>'
            ),
        ),
        page.section(
            "Survival of unseen stress",
            page.panel(bar_chart(bars, "Holdout stressors survived")),
        ),
        page.section(
            "Per-stressor judgments",
            page.panel(
                page.table(
                    ("id", "Naïve", "Residual", "Mechanism (residual)"),
                    _judgment_rows(ctx),
                    table_id="rz-judgments",
                    filterable=True,
                )
            ),
        ),
    ]
    sections += report_mod.gate_section(gate)
    return report_mod.document(ctx, spec, sections)
