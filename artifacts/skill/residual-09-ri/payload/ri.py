"""The empirical test: does the analysis actually buy anything?

``Ri = (Y - X) / S`` over a set of holdout stressors that were never used to
design either architecture, where X is what the naïve architecture survives and
Y is what the residual one survives (residuality-theory §empirical-test). It is the part of
residuality that is falsifiable, and it only stays falsifiable if two things
hold:

* the holdout never saw the residues -- enforced by generating it in its own
  blind units, and checked for leakage against the training register by the
  ``08-holdout`` skill's gate;
* the judge never knows which architecture is which -- enforced by presenting
  them as A and B, with the assignment derived from a hash of the run slug so it
  is reproducible without being guessable from the step alone.

A human running this by hand can do neither. That is the one place where doing
this with agents is not merely faster but methodologically better.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from residual.model import Judgment

ARCHITECTURES: tuple[str, ...] = ("naive", "residual")
LABELS: tuple[str, ...] = ("A", "B")


@dataclass(frozen=True)
class RiResult:
    stressors: int = 0
    naive_survivals: int = 0
    residual_survivals: int = 0
    ri: float = 0.0
    blind: bool = False
    judge_model: str = ""
    judged_both: tuple[str, ...] = ()
    judged_one: tuple[str, ...] = ()
    unjudged: tuple[str, ...] = ()
    duplicates: tuple[tuple[str, str], ...] = ()
    stats: Mapping[str, object] = field(default_factory=dict)


def label_map(slug: str) -> dict[str, str]:
    """Which label each architecture wears in this run.

    Derived from the slug rather than a random number so the mapping survives a
    crash, a different machine and a re-render -- but is not the same for every
    run, so a judge cannot learn that "A is always the good one".
    """
    digest = hashlib.sha256(slug.encode("utf-8")).digest()
    flipped = digest[0] % 2 == 1
    if flipped:
        return {"naive": "B", "residual": "A"}
    return {"naive": "A", "residual": "B"}


def architecture_of(slug: str, label: str) -> str:
    """Invert :func:`label_map`: which architecture a judgment was about."""
    mapping = label_map(slug)
    for architecture, assigned in mapping.items():
        if assigned == label.strip().upper():
            return architecture
    raise ValueError(f"unknown architecture label {label!r}; expected A or B")


def _by_stressor(
    judgments: Sequence[Judgment], slug: str
) -> tuple[dict[str, dict[str, Judgment]], tuple[tuple[str, str], ...]]:
    grouped: dict[str, dict[str, Judgment]] = {}
    duplicates: list[tuple[str, str]] = []
    for judgment in judgments:
        try:
            architecture = architecture_of(slug, judgment.arch)
        except ValueError:
            continue
        slot = grouped.setdefault(judgment.stressor_id, {})
        if architecture in slot:
            duplicates.append((judgment.stressor_id, judgment.arch))
            continue
        slot[architecture] = judgment
    return grouped, tuple(sorted(duplicates))


def score(
    judgments: Sequence[Judgment],
    holdout_ids: Sequence[str],
    slug: str,
    blind: bool = True,
) -> RiResult:
    """Tally X, Y and Ri over the stressors judged for *both* architectures.

    Judging one architecture but not the other would bias the difference, so a
    half-judged stressor is excluded from S and reported rather than counted.
    """
    grouped, duplicates = _by_stressor(judgments, slug)

    judged_both = tuple(
        sorted(sid for sid, slot in grouped.items() if len(slot) == len(ARCHITECTURES))
    )
    judged_one = tuple(sorted(sid for sid, slot in grouped.items() if len(slot) == 1))
    unjudged = tuple(sorted(set(holdout_ids) - set(grouped)))

    x = sum(1 for sid in judged_both if grouped[sid]["naive"].survives)
    y = sum(1 for sid in judged_both if grouped[sid]["residual"].survives)
    s = len(judged_both)
    ri = round((y - x) / s, 4) if s else 0.0

    models = {
        j.provenance.model for j in judgments if j.provenance.model
    }
    return RiResult(
        stressors=s,
        naive_survivals=x,
        residual_survivals=y,
        ri=ri,
        blind=blind,
        judge_model=", ".join(sorted(models)),
        judged_both=judged_both,
        judged_one=judged_one,
        unjudged=unjudged,
        duplicates=duplicates,
        stats={
            "S": s,
            "X": x,
            "Y": y,
            "Ri": ri,
            "naive_rate": round(x / s, 4) if s else 0.0,
            "residual_rate": round(y / s, 4) if s else 0.0,
            "holdout_total": len(holdout_ids),
            "coverage": round(s / len(holdout_ids), 4) if holdout_ids else 0.0,
        },
    )


def interpret(result: RiResult) -> str:
    """One sentence on what the number means, with its caveats attached.

    Ri is a direction, not a grade. It is comparable only within one judge model
    and one execution mode, and it says nothing about whether the architecture
    is good -- only whether this round of work moved it toward criticality
    (residuality-theory §empirical-test).
    """
    if not result.stressors:
        return "No stressor was judged for both architectures, so Ri is undefined."

    if result.ri > 0:
        verdict = (
            f"Ri = {result.ri:+.2f}: the residual architecture survived "
            f"{result.residual_survivals - result.naive_survivals} more of "
            f"{result.stressors} unseen stressors than the naïve one. The work "
            "moved toward criticality."
        )
    elif result.ri == 0:
        verdict = (
            f"Ri = 0.00 over {result.stressors} unseen stressors: this round of "
            "analysis bought nothing measurable. Further rounds have diminishing "
            "returns."
        )
    else:
        verdict = (
            f"Ri = {result.ri:+.2f}: the residual architecture survived *fewer* "
            "unseen stressors than the naïve one. Either the added components "
            "introduced their own fragility, or the judging is not reliable."
        )

    caveats = ["comparable only within one judge model and one execution mode"]
    if not result.blind:
        caveats.append("NOT blind — some records were generated in a shared context")
    if result.judged_one:
        caveats.append(f"{len(result.judged_one)} stressor(s) judged for one architecture only")
    if result.unjudged:
        caveats.append(f"{len(result.unjudged)} holdout stressor(s) never judged")

    return f"{verdict} ({'; '.join(caveats)}.)"
