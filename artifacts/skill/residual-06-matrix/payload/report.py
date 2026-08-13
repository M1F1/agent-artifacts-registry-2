"""The contagion report: the heatmap and the refactoring triggers behind it.

Every panel is framed as an argument to have rather than an instruction to
follow. The matrix cannot tell you whether a hot column wants splitting or
wants redundancy -- that is the conversation (residuality-theory §the-artifacts).
"""

from __future__ import annotations

from residual.model import GateResult, StepSpec
from residual.render import page
from residual.render import report as report_mod
from residual.render.svg import Bar, bar_chart, heatmap
from residual.run import RunContext


def build(
    ctx: RunContext, spec: StepSpec, built, triggers, gate: GateResult
) -> str:
    stats = triggers.stats
    tiles = [
        ("Stressors", str(stats.get("stressors", 0)), "matrix rows"),
        ("Components", str(stats.get("components", 0)), "matrix columns"),
        ("N", str(stats.get("n", 0)), "nodes: rows + columns"),
        ("K", str(stats.get("k", 0)), "links: cells set to 1"),
        ("Density", f"{float(stats.get('density', 0)):.1%}", "K over all cells"),
    ]

    rows = tuple(
        (s, tuple(built.hit(s, c) for c in built.components)) for s in built.stressors
    )

    sections = [
        page.tiles(tiles),
        page.section(
            "The matrix",
            page.panel(heatmap(built.components, rows, "Contagion matrix")),
        ),
        page.section(
            "Trigger 1 — stressors with the widest blast radius",
            page.panel(
                bar_chart(
                    tuple(
                        Bar(label=s, value=float(n), note=str(n))
                        for s, n in triggers.hottest_stressors
                    ),
                    "Components reached per stressor",
                )
                + '<p class="rz-note">High rows are where the hyperliminal '
                "coupling lives, and where the non-functional concerns nobody "
                "could elicit turn out to have been hiding.</p>"
            ),
        ),
        page.section(
            "Trigger 2 — components most sensitive to stress",
            page.panel(
                bar_chart(
                    tuple(
                        Bar(label=c, value=float(n), note=str(n))
                        for c, n in triggers.hottest_components
                    ),
                    "Stressors reaching each component",
                )
                + '<p class="rz-note">Either the component is doing too many '
                "things and wants splitting, or it is genuinely central and wants "
                "redundancy. The matrix cannot tell you which — that is the "
                "conversation.</p>"
            ),
        ),
        page.section(
            "Trigger 3 — coupling revealed by shared stress",
            page.panel(
                page.table(
                    ("Component", "Component", "Shared stressors"),
                    [(a, b, str(n)) for a, b, n in triggers.coupling_pairs],
                )
                + '<p class="rz-note">If these two have no functional dependency '
                "on each other, you have found hyperliminal coupling: invisible "
                "until the stressor lands (residuality-theory §contagion-analysis).</p>"
            ),
        ),
        page.section(
            "Trigger 4 — merge candidates",
            page.panel(
                page.table(
                    ("Components with identical response to stress",),
                    [(", ".join(group),) for group in triggers.merge_candidates],
                )
                + '<p class="rz-note">These live and die together, so a change to '
                "one is a change to the other. Merging them lowers N and the "
                "operational cost that comes with it.</p>"
            ),
        ),
    ]
    sections += report_mod.gate_section(gate)
    return report_mod.document(ctx, spec, sections)
