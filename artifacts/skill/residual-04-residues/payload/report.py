"""The residue report: what got designed, and how much of it was already there.

Looping gets a panel of its own because it is the one number in the pipeline
readers reliably misread as a failure.
"""

from __future__ import annotations

from collections import Counter
from typing import Sequence

from residual.model import GateResult, StepSpec
from residual.render import page
from residual.render import report as report_mod
from residual.render.svg import Bar, bar_chart
from residual.run import RunContext


def build(
    ctx: RunContext, spec: StepSpec, residues: Sequence, gate: GateResult
) -> str:
    looping = int(gate.stats.get("looping", 0))
    total = int(gate.stats.get("residues", 0)) or 1
    tiles = [
        ("Residues", str(gate.stats.get("residues", 0)), "one per stressor"),
        (
            "Looping",
            f"{looping / total:.0%}",
            "already survived by an earlier residue",
        ),
        (
            "Components",
            str(gate.stats.get("distinct_components", 0)),
            "named across all residues",
        ),
        ("Gate", "pass" if gate.ok else "fail", f"{len(gate.errors)} errors"),
    ]

    counts = Counter(c for r in residues for c in r.components)
    bars = tuple(
        Bar(label=name, value=float(n), note=str(n))
        for name, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
    )

    sections = [
        page.tiles(tiles),
        page.section(
            "Looping",
            page.panel(
                '<p class="rz-note">Looping is the result, not a gap. When new '
                "stressors keep turning out to be survived by residues written "
                "earlier, the architecture is approaching criticality "
                "(residuality-theory §looping-and-convergence). A rate near zero means there is more "
                "stressing to do; a rate that climbs and then plateaus is the "
                "signal to stop.</p>"
            ),
        ),
        page.section(
            "Components most often demanded",
            page.panel(bar_chart(bars, "Residues naming each component")),
        ),
        page.section(
            "Residues",
            page.panel(
                page.table(
                    ("id", "Stressor", "Change", "Components", "Already survived by"),
                    [
                        (
                            r.id,
                            r.stressor_id,
                            r.change or "—",
                            ", ".join(r.components) or "—",
                            ", ".join(r.already_survived_by) or "—",
                        )
                        for r in residues
                    ],
                    table_id="rz-residues",
                    filterable=True,
                )
            ),
        ),
    ]
    sections += report_mod.gate_section(gate)
    return report_mod.document(ctx, spec, sections)
