"""Data to SVG: pure functions, deterministic output.

The rules that make "hand-rolled HTML" a standard rather than a habit:

* no randomness, no clock, no force-directed layout -- identical input must
  produce byte-identical output, or the golden tests mean nothing;
* every coordinate is rounded to two decimals before formatting, so float repr
  cannot differ between platforms;
* colour comes from CSS variables defined by the page shell, never literals, so
  charts follow the reader's light or dark theme.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Sequence

LABEL_WIDTH = 210
VALUE_WIDTH = 56
BAR_HEIGHT = 20
BAR_GAP = 7


@dataclass(frozen=True)
class Bar:
    label: str
    value: float
    note: str = ""
    tone: str = "accent"


def num(value: float) -> str:
    """Fixed two-decimal formatting; the only way numbers reach the output."""
    return f"{round(float(value), 2):.2f}"


def _open(width: int, height: int, title: str) -> str:
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'role="img" aria-label="{escape(title)}" '
        'xmlns="http://www.w3.org/2000/svg" class="rz-chart">'
    )


def bar_chart(bars: Sequence[Bar], title: str, width: int = 680) -> str:
    """Horizontal bars, sorted by the caller, labelled on the left."""
    if not bars:
        return '<p class="rz-empty">No data.</p>'

    height = len(bars) * (BAR_HEIGHT + BAR_GAP) + BAR_GAP
    ceiling = max((b.value for b in bars), default=0) or 1
    track = width - LABEL_WIDTH - VALUE_WIDTH

    parts = [_open(width, height, title)]
    for index, bar in enumerate(bars):
        y = BAR_GAP + index * (BAR_HEIGHT + BAR_GAP)
        length = max(track * (bar.value / ceiling), 1.0)
        text_y = y + BAR_HEIGHT * 0.72
        parts.append(
            f'<text class="rz-bar-label" x="{num(LABEL_WIDTH - 10)}" '
            f'y="{num(text_y)}" text-anchor="end">{escape(bar.label)}</text>'
        )
        parts.append(
            f'<rect class="rz-bar rz-{escape(bar.tone)}" x="{num(LABEL_WIDTH)}" '
            f'y="{num(y)}" width="{num(length)}" height="{BAR_HEIGHT}" rx="3">'
            f"<title>{escape(bar.label)}: {escape(bar.note or num(bar.value))}</title>"
            "</rect>"
        )
        parts.append(
            f'<text class="rz-bar-value" x="{num(LABEL_WIDTH + length + 8)}" '
            f'y="{num(text_y)}">{escape(bar.note or num(bar.value))}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def heatmap(
    columns: Sequence[str],
    rows: Sequence[tuple[str, Sequence[int]]],
    title: str,
    cell: int = 13,
    max_rows: int = 120,
) -> str:
    """The contagion matrix as a grid: stressor rows against component columns.

    Row labels are omitted -- a register runs to hundreds of rows and the ids
    would be unreadable at this size. The shape is what carries the information:
    dense rows are the stressors with the widest blast radius, dense columns the
    components most sensitive to stress. Hover gives the identifiers.
    """
    if not columns or not rows:
        return '<p class="rz-empty">No matrix yet.</p>'

    shown = list(rows[:max_rows])
    # Row ids are only legible while there are few of them. Past that the shape
    # is what carries the information and the labels are noise, so the gutter
    # collapses rather than leaving a band of empty space.
    label_rows = len(shown) <= 60
    gutter = 52 if label_rows else 6
    label_h = 8 * max((len(c) for c in columns), default=8) + 12
    width = gutter + len(columns) * cell + 20
    height = label_h + len(shown) * cell + 10

    parts = [_open(width, height, title)]
    for index, name in enumerate(columns):
        x = gutter + index * cell + cell * 0.72
        parts.append(
            f'<text class="rz-axis" x="{num(x)}" y="{num(label_h - 6)}" '
            f'transform="rotate(-60 {num(x)} {num(label_h - 6)})">{escape(name)}</text>'
        )

    for r, (row_id, values) in enumerate(shown):
        y = label_h + r * cell
        if label_rows:
            parts.append(
                f'<text class="rz-axis" x="{num(gutter - 6)}" '
                f'y="{num(y + cell * 0.72)}" text-anchor="end">{escape(row_id)}</text>'
            )
        for c, value in enumerate(values[: len(columns)]):
            x = gutter + c * cell
            tone = "rz-cell-on" if value else "rz-cell-off"
            parts.append(
                f'<rect class="rz-cell {tone}" x="{num(x)}" y="{num(y)}" '
                f'width="{cell - 1}" height="{cell - 1}" rx="1">'
                f"<title>{escape(row_id)} × {escape(columns[c])}: {value}</title></rect>"
            )

    parts.append("</svg>")
    svg = "".join(parts)
    if len(rows) > max_rows:
        svg += (
            f'<p class="rz-note">Showing the first {max_rows} of {len(rows)} '
            "rows. The full matrix is in <code>matrix.csv</code>.</p>"
        )
    return svg


def line_chart(
    points: Sequence[tuple[str, float]],
    title: str,
    width: int = 680,
    height: int = 220,
    y_max: float | None = None,
) -> str:
    """A single series against evenly spaced, ordered x labels."""
    if len(points) < 2:
        return '<p class="rz-empty">Not enough points yet.</p>'

    pad_left, pad_right, pad_top, pad_bottom = 44, 12, 14, 30
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom
    ceiling = y_max if y_max is not None else max(v for _, v in points)
    ceiling = ceiling or 1.0

    def x_at(i: int) -> float:
        return pad_left + plot_w * (i / (len(points) - 1))

    def y_at(v: float) -> float:
        return pad_top + plot_h * (1 - min(v / ceiling, 1.0))

    parts = [_open(width, height, title)]
    for fraction in (0.0, 0.5, 1.0):
        y = pad_top + plot_h * fraction
        parts.append(
            f'<line class="rz-grid" x1="{num(pad_left)}" y1="{num(y)}" '
            f'x2="{num(width - pad_right)}" y2="{num(y)}" />'
        )
        parts.append(
            f'<text class="rz-axis" x="{num(pad_left - 8)}" y="{num(y + 4)}" '
            f'text-anchor="end">{num(ceiling * (1 - fraction))}</text>'
        )

    path = " ".join(
        f"{'M' if i == 0 else 'L'}{num(x_at(i))} {num(y_at(v))}"
        for i, (_, v) in enumerate(points)
    )
    parts.append(f'<path class="rz-line" d="{path}" fill="none" />')

    for i, (label, value) in enumerate(points):
        parts.append(
            f'<circle class="rz-dot" cx="{num(x_at(i))}" cy="{num(y_at(value))}" r="3">'
            f"<title>{escape(label)}: {num(value)}</title></circle>"
        )
        parts.append(
            f'<text class="rz-axis" x="{num(x_at(i))}" y="{num(height - 8)}" '
            f'text-anchor="middle">{escape(label)}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)
