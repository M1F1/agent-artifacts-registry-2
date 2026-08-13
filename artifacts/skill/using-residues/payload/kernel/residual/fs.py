"""Every filesystem touch in the kernel goes through this module.

Callers hand in paths and get plain data back.  All writers are atomic: content
goes to a sibling temp file and is then ``os.replace``d into position, so an
agent killed mid-write can never leave a half-formed artifact in a run
directory that another agent is about to read.

Writers are also deterministic -- fixed newline, sorted JSON keys, trailing
newline -- so that identical input produces byte-identical output and the
golden tests mean something.
"""

from __future__ import annotations

import csv
import json
import os
import tomllib
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

ENCODING = "utf-8"
NEWLINE = "\n"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, content: str) -> Path:
    """Atomically write *content*, creating parent directories as needed."""
    ensure_dir(path.parent)
    tmp = path.with_name(f".{path.name}.tmp{os.getpid()}")
    tmp.write_text(content, encoding=ENCODING, newline=NEWLINE)
    os.replace(tmp, path)
    return path


def read_text(path: Path) -> str:
    return path.read_text(encoding=ENCODING)


def read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def dumps_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + NEWLINE


def write_json(path: Path, data: Any) -> Path:
    return write_text(path, dumps_json(data))


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def dumps_jsonl(records: Iterable[Mapping[str, Any]]) -> str:
    lines = (json.dumps(r, sort_keys=True, ensure_ascii=False) for r in records)
    return "".join(line + NEWLINE for line in lines)


def write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> Path:
    return write_text(path, dumps_jsonl(records))


def read_jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    """Read a JSONL file, skipping blank lines.

    A malformed line raises, deliberately: a shard that cannot be parsed should
    fail its gate and go back to the queue rather than silently shrink.
    """
    if not path.exists():
        return ()
    out: list[dict[str, Any]] = []
    for number, line in enumerate(read_text(path).splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            out.append(json.loads(stripped))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: {exc.msg}") from exc
    return tuple(out)


def dumps_csv(columns: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> str:
    import io

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=list(columns),
        lineterminator=NEWLINE,
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in columns})
    return buffer.getvalue()


def write_csv(
    path: Path, columns: Sequence[str], rows: Iterable[Mapping[str, Any]]
) -> Path:
    return write_text(path, dumps_csv(columns, rows))


def read_csv(path: Path) -> tuple[dict[str, str], ...]:
    if not path.exists():
        return ()
    with path.open("r", encoding=ENCODING, newline="") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle))


def iter_files(directory: Path, suffix: str = "") -> Iterator[Path]:
    """Yield files in *directory* in name order.

    Sorted, because deterministic ordering is what makes compiled artifacts
    reproducible across a parallel run and a sequential one.
    """
    if not directory.exists():
        return
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.name.endswith(suffix) and not path.name.startswith("."):
            yield path


def move(source: Path, destination: Path) -> Path:
    """Atomic move within a filesystem; the basis of queue claiming."""
    ensure_dir(destination.parent)
    os.replace(source, destination)
    return destination
