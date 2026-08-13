"""Contagion analysis: the incidence matrix and its refactoring triggers.

The matrix maps stressors against components -- relationships *across* the
hyperliminal boundary, not the domain mapping traditional methods draw
(residuality-theory §contagion-analysis). Every number here is arithmetic over 1s and 0s. No model
ever computes a total, because a model that miscounts a column produces a
plausible-looking refactoring plan built on a wrong number.

The seven triggers are the book's own (residuality-theory §contagion-analysis-539). They are
prompts for an argument, not instructions: the value of the matrix is the
conversation it starts.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from residual.model import Component, MatrixRow


@dataclass(frozen=True)
class Matrix:
    """Stressor rows against component columns, both in stable order."""

    components: tuple[str, ...]
    stressors: tuple[str, ...]
    cells: Mapping[str, frozenset[str]]

    def hit(self, stressor: str, component: str) -> int:
        return 1 if component in self.cells.get(stressor, frozenset()) else 0

    def row_total(self, stressor: str) -> int:
        return len(self.cells.get(stressor, frozenset()) & set(self.components))

    def column_total(self, component: str) -> int:
        return sum(1 for s in self.stressors if component in self.cells.get(s, ()))

    def signature(self, component: str) -> tuple[int, ...]:
        """A component's response to every stressor, as an ordered vector."""
        return tuple(self.hit(s, component) for s in self.stressors)


@dataclass(frozen=True)
class Triggers:
    """The seven refactoring signals, plus the network figures behind them."""

    n: int = 0
    k: int = 0
    density: float = 0.0
    hottest_stressors: tuple[tuple[str, int], ...] = ()
    hottest_components: tuple[tuple[str, int], ...] = ()
    coupling_pairs: tuple[tuple[str, str, int], ...] = ()
    merge_candidates: tuple[tuple[str, ...], ...] = ()
    untouched_components: tuple[str, ...] = ()
    unmapped_stressors: tuple[str, ...] = ()
    stats: Mapping[str, object] = field(default_factory=dict)


def build(rows: Sequence[MatrixRow], components: Sequence[Component]) -> Matrix:
    """Assemble the matrix, keeping only hits that name a real component.

    An agent naming a component that does not exist is a gate finding, not
    something to silently invent a column for.
    """
    names = tuple(c.name for c in components)
    known = set(names)
    cells = {
        row.stressor_id: frozenset(h for h in row.hits if h in known) for row in rows
    }
    return Matrix(
        components=names,
        stressors=tuple(sorted(cells)),
        cells=cells,
    )


def unknown_components(
    rows: Sequence[MatrixRow], components: Sequence[Component]
) -> tuple[tuple[str, str], ...]:
    """(stressor, name) pairs naming something absent from the architecture."""
    known = {c.name for c in components}
    return tuple(
        (row.stressor_id, hit)
        for row in rows
        for hit in row.hits
        if hit not in known
    )


def coupling_pairs(matrix: Matrix) -> tuple[tuple[str, str, int], ...]:
    """Component pairs hit by the same stressor, ranked by how often.

    Trigger 3. Two 1s in a row is coupling, and if the components have no
    functional dependency on each other it is *hyperliminal* coupling -- the
    invisible kind that only shows up when the stressor lands
    (residuality-theory §contagion-analysis). This is where the non-functional requirements
    everybody struggles to elicit turn out to have been hiding.
    """
    tally: Counter[tuple[str, str]] = Counter()
    order = {name: i for i, name in enumerate(matrix.components)}
    for stressor in matrix.stressors:
        hits = sorted(matrix.cells.get(stressor, ()), key=lambda n: order.get(n, 0))
        for i in range(len(hits)):
            for j in range(i + 1, len(hits)):
                tally[(hits[i], hits[j])] += 1
    return tuple(
        (left, right, count)
        for (left, right), count in sorted(
            tally.items(), key=lambda kv: (-kv[1], kv[0])
        )
    )


def merge_candidates(matrix: Matrix) -> tuple[tuple[str, ...], ...]:
    """Components with identical response signatures.

    Trigger 4. Two components that live and die together will always be changed
    together, so they can be one component -- which lowers N and the operational
    cost that comes with it (residuality-theory §contagion-analysis). Components nothing touches are
    excluded: their signatures match trivially and say nothing.
    """
    groups: dict[tuple[int, ...], list[str]] = {}
    for name in matrix.components:
        signature = matrix.signature(name)
        if any(signature):
            groups.setdefault(signature, []).append(name)
    return tuple(
        tuple(sorted(names)) for names in groups.values() if len(names) > 1
    )


def triggers(matrix: Matrix, top: int = 10) -> Triggers:
    rows = matrix.stressors
    cols = matrix.components
    k = sum(matrix.row_total(s) for s in rows)
    cells = len(rows) * len(cols)

    hottest_rows = tuple(
        sorted(
            ((s, matrix.row_total(s)) for s in rows),
            key=lambda kv: (-kv[1], kv[0]),
        )
    )
    hottest_cols = tuple(
        sorted(
            ((c, matrix.column_total(c)) for c in cols),
            key=lambda kv: (-kv[1], kv[0]),
        )
    )

    return Triggers(
        n=len(rows) + len(cols),
        k=k,
        density=round(k / cells, 4) if cells else 0.0,
        hottest_stressors=hottest_rows[:top],
        hottest_components=hottest_cols[:top],
        coupling_pairs=coupling_pairs(matrix)[:top],
        merge_candidates=merge_candidates(matrix),
        untouched_components=tuple(c for c, total in hottest_cols if total == 0),
        unmapped_stressors=tuple(s for s, total in hottest_rows if total == 0),
        stats={
            "stressors": len(rows),
            "components": len(cols),
            "n": len(rows) + len(cols),
            "k": k,
            "density": round(k / cells, 4) if cells else 0.0,
            "mean_row_total": round(k / len(rows), 2) if rows else 0.0,
            "mean_column_total": round(k / len(cols), 2) if cols else 0.0,
        },
    )


def to_rows(matrix: Matrix) -> tuple[dict[str, str], ...]:
    """The matrix as CSV rows, mirroring the book's table with a totals row."""
    out: list[dict[str, str]] = []
    for stressor in matrix.stressors:
        row: dict[str, str] = {"stressor": stressor}
        for component in matrix.components:
            row[component] = str(matrix.hit(stressor, component))
        row["total"] = str(matrix.row_total(stressor))
        out.append(row)

    totals: dict[str, str] = {"stressor": "TOTAL"}
    for component in matrix.components:
        totals[component] = str(matrix.column_total(component))
    totals["total"] = str(sum(matrix.row_total(s) for s in matrix.stressors))
    out.append(totals)
    return tuple(out)


def columns(matrix: Matrix) -> tuple[str, ...]:
    return ("stressor", *matrix.components, "total")
