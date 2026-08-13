"""The HTML shell: one self-contained file, no network, both themes.

Everything is inline. A report has to open from a file:// path on a locked-down
laptop, survive being mailed as an attachment, and render the same in a light
and a dark browser. That rules out CDNs, web fonts and remote images.

No timestamp is written into the body. The kernel never reads the clock, and a
report that changed every time it was generated could not be golden-tested.
"""

from __future__ import annotations

from html import escape
from typing import Iterable, Mapping, Sequence

CSS = """
:root {
  color-scheme: light dark;
  --rz-bg: #fbfbfa; --rz-panel: #ffffff; --rz-ink: #1c1b19; --rz-muted: #6b6a67;
  --rz-line: #e3e2df; --rz-accent: #3f6f9f; --rz-warn: #a8742a; --rz-bad: #a4433a;
  --rz-grid: #eceae7;
}
@media (prefers-color-scheme: dark) {
  :root {
    --rz-bg: #17181a; --rz-panel: #1e2023; --rz-ink: #e9e8e6; --rz-muted: #9b9a97;
    --rz-line: #32353a; --rz-accent: #7aa7d4; --rz-warn: #d4a959; --rz-bad: #d98a80;
    --rz-grid: #292c30;
  }
}
:root[data-theme="light"] {
  --rz-bg: #fbfbfa; --rz-panel: #ffffff; --rz-ink: #1c1b19; --rz-muted: #6b6a67;
  --rz-line: #e3e2df; --rz-accent: #3f6f9f; --rz-warn: #a8742a; --rz-bad: #a4433a;
  --rz-grid: #eceae7;
}
:root[data-theme="dark"] {
  --rz-bg: #17181a; --rz-panel: #1e2023; --rz-ink: #e9e8e6; --rz-muted: #9b9a97;
  --rz-line: #32353a; --rz-accent: #7aa7d4; --rz-warn: #d4a959; --rz-bad: #d98a80;
  --rz-grid: #292c30;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 2rem 1.25rem 4rem; background: var(--rz-bg); color: var(--rz-ink);
  font: 15px/1.55 ui-sans-serif, -apple-system, "Segoe UI", Roboto, Helvetica, sans-serif;
}
.rz-wrap { max-width: 1080px; margin: 0 auto; }
h1 { font-size: 1.5rem; margin: 0 0 .25rem; letter-spacing: -0.01em; }
h2 { font-size: 1.05rem; margin: 2rem 0 .75rem; letter-spacing: -0.01em; }
.rz-sub { color: var(--rz-muted); margin: 0 0 1.5rem; }
.rz-panel {
  background: var(--rz-panel); border: 1px solid var(--rz-line);
  border-radius: 10px; padding: 1rem 1.15rem; margin-bottom: 1rem; overflow-x: auto;
}
.rz-tiles { display: grid; gap: .75rem; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
.rz-tile { background: var(--rz-panel); border: 1px solid var(--rz-line); border-radius: 10px; padding: .85rem 1rem; }
.rz-tile .v { font-size: 1.5rem; font-variant-numeric: tabular-nums; }
.rz-tile .k { color: var(--rz-muted); font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; }
.rz-tile .n { color: var(--rz-muted); font-size: .78rem; margin-top: .3rem; }
table { border-collapse: collapse; width: 100%; font-size: .88rem; }
th, td { text-align: left; padding: .45rem .6rem; border-bottom: 1px solid var(--rz-line); vertical-align: top; }
th { color: var(--rz-muted); font-weight: 600; font-size: .76rem; text-transform: uppercase; letter-spacing: .04em; }
td.rz-id { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; white-space: nowrap; color: var(--rz-muted); }
.rz-chart { display: block; max-width: 100%; }
.rz-bar { fill: var(--rz-accent); }
.rz-bar.rz-warn { fill: var(--rz-warn); }
.rz-bar.rz-bad { fill: var(--rz-bad); }
.rz-bar-label, .rz-bar-value, .rz-axis { fill: var(--rz-muted); font-size: 11px; }
.rz-bar-value { fill: var(--rz-ink); font-variant-numeric: tabular-nums; }
.rz-grid { stroke: var(--rz-grid); stroke-width: 1; }
.rz-line { stroke: var(--rz-accent); stroke-width: 2; }
.rz-dot { fill: var(--rz-accent); }
.rz-empty { color: var(--rz-muted); font-style: italic; }
.rz-cell-on { fill: var(--rz-accent); }
.rz-cell-off { fill: var(--rz-grid); }
.rz-verdict { font-size: 1.02rem; line-height: 1.6; margin: 0; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .86em; }
.rz-pill { display: inline-block; padding: .1rem .45rem; border-radius: 99px; font-size: .74rem; border: 1px solid var(--rz-line); color: var(--rz-muted); }
.rz-pill.err { color: var(--rz-bad); border-color: var(--rz-bad); }
.rz-pill.warn { color: var(--rz-warn); border-color: var(--rz-warn); }
.rz-filter {
  width: 100%; padding: .5rem .65rem; border-radius: 8px; margin-bottom: .75rem;
  border: 1px solid var(--rz-line); background: var(--rz-bg); color: var(--rz-ink); font: inherit;
}
.rz-note { color: var(--rz-muted); font-size: .82rem; margin: .4rem 0 0; }
"""

FILTER_JS = """
document.querySelectorAll('[data-filter-for]').forEach(function (input) {
  var table = document.getElementById(input.getAttribute('data-filter-for'));
  if (!table) return;
  input.addEventListener('input', function () {
    var needle = input.value.toLowerCase();
    table.querySelectorAll('tbody tr').forEach(function (row) {
      row.style.display = row.textContent.toLowerCase().indexOf(needle) === -1 ? 'none' : '';
    });
  });
});
"""


class Raw(str):
    """A cell that is already HTML and must not be escaped again."""


def tile(key: str, value: str, note: str = "") -> str:
    note_html = f'<div class="n">{escape(note)}</div>' if note else ""
    return (
        f'<div class="rz-tile"><div class="k">{escape(key)}</div>'
        f'<div class="v">{escape(value)}</div>{note_html}</div>'
    )


def tiles(items: Sequence[tuple[str, str, str]]) -> str:
    return '<div class="rz-tiles">' + "".join(tile(*i) for i in items) + "</div>"


def table(
    columns: Sequence[str],
    rows: Iterable[Sequence[str]],
    table_id: str = "",
    filterable: bool = False,
) -> str:
    ident = f' id="{escape(table_id)}"' if table_id else ""
    head = "".join(f"<th>{escape(c)}</th>" for c in columns)
    id_column = bool(columns) and columns[0].lower() in ("id", "#")

    def cell_html(value: object) -> str:
        return str(value) if isinstance(value, Raw) else escape(str(value))

    body = "".join(
        "<tr>"
        + "".join(
            f'<td class="rz-id">{cell_html(value)}</td>'
            if index == 0 and id_column
            else f"<td>{cell_html(value)}</td>"
            for index, value in enumerate(row)
        )
        + "</tr>"
        for row in rows
    )
    search = (
        f'<input class="rz-filter" type="search" placeholder="Filter rows…" '
        f'data-filter-for="{escape(table_id)}">'
        if filterable and table_id
        else ""
    )
    return (
        f"{search}<table{ident}><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    )


def panel(body: str) -> str:
    return f'<div class="rz-panel">{body}</div>'


def section(heading: str, body: str) -> str:
    return f"<h2>{escape(heading)}</h2>{body}"


def document(title: str, subtitle: str, sections: Sequence[str]) -> str:
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{escape(title)}</title>",
            f"<style>{CSS}</style>",
            "</head>",
            "<body>",
            '<div class="rz-wrap">',
            f"<h1>{escape(title)}</h1>",
            f'<p class="rz-sub">{escape(subtitle)}</p>',
            *sections,
            "</div>",
            f"<script>{FILTER_JS}</script>",
            "</body>",
            "</html>",
            "",
        ]
    )
