"""Stdlib-only text comparison, used by the gates.

There are no embeddings here.  Similarity is lexical: a token-set cosine plus
a character-level ratio from :mod:`difflib`.  That is enough to catch
restatement, copy-paste and near-duplicates, and it is deterministic, which
matters more for a gate than recall does.

It will not catch two stressors that mean the same thing in disjoint
vocabulary.  Every redundancy figure this module produces is therefore a lower
bound, and the report says so.
"""

from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Iterable, Sequence

_WORD = re.compile(r"[a-z0-9]+")

#: Words too common to carry signal in a similarity or specificity comparison.
STOPWORDS: frozenset[str] = frozenset(
    """
    a an and are as at be been but by can could do does for from has have if in
    into is it its may might must no not of on or our so than that the their
    then there these they this to was we were what when which who will with
    would you your
    """.split()
)


def normalise(text: str) -> str:
    return " ".join(_WORD.findall(text.lower()))


def tokens(text: str, drop_stopwords: bool = True) -> tuple[str, ...]:
    found = _WORD.findall(text.lower())
    if drop_stopwords:
        found = [t for t in found if t not in STOPWORDS]
    return tuple(found)


def token_cosine(left: str, right: str) -> float:
    """Cosine over token counts.  1.0 for identical bags, 0.0 for disjoint."""
    a, b = Counter(tokens(left)), Counter(tokens(right))
    if not a or not b:
        return 0.0
    shared = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in shared)
    if not dot:
        return 0.0
    norm_a = sum(v * v for v in a.values()) ** 0.5
    norm_b = sum(v * v for v in b.values()) ** 0.5
    # Clamped: floating point makes identical bags score 1.0000000000000002,
    # and a similarity above 1.0 would be nonsense to compare a threshold to.
    return min(dot / (norm_a * norm_b), 1.0)


def sequence_ratio(left: str, right: str) -> float:
    """Character-level similarity of the normalised strings."""
    return SequenceMatcher(None, normalise(left), normalise(right)).ratio()


def similarity(left: str, right: str) -> float:
    """Conservative similarity: the higher of the two measures.

    Taking the max makes the gates trigger more often, which is the right bias.
    A false near-duplicate flag costs a human ten seconds; a missed one silently
    inflates the stressor count and makes the register look broader than it is.
    """
    return max(token_cosine(left, right), sequence_ratio(left, right))


def near_duplicates(
    texts: Sequence[str], threshold: float
) -> tuple[tuple[int, int, float], ...]:
    """All index pairs scoring at or above *threshold*, in stable order.

    Quadratic, which is fine: a stressor register is a few hundred rows, and
    keeping it obvious beats keeping it clever.
    """
    out: list[tuple[int, int, float]] = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            score = similarity(texts[i], texts[j])
            if score >= threshold:
                out.append((i, j, round(score, 4)))
    return tuple(out)


def specificity(text: str, vocabulary: Iterable[str]) -> int:
    """How many distinct domain terms *text* actually mentions.

    The stand-in for the domain-swap test (residuality-theory §stressors): a stressor that
    names nothing from this system's own vocabulary would read identically in
    any other company's analysis, and is generic by construction.
    """
    present = set(tokens(text, drop_stopwords=False))
    hits = set()
    for raw in vocabulary:
        term = str(raw).strip().lower()
        if not term:
            continue
        parts = set(tokens(term, drop_stopwords=False))
        if parts and parts <= present:
            hits.add(term)
    return len(hits)


def marker_hits(text: str, markers: Iterable[str]) -> tuple[str, ...]:
    """Which of *markers* appear in *text*, for the technical-quota gate."""
    lowered = normalise(text)
    return tuple(m for m in markers if normalise(m) and normalise(m) in lowered)


def vocabulary_from(*sources: Iterable[str]) -> tuple[str, ...]:
    """Deduplicated, sorted domain vocabulary built from flows, actors, etc."""
    seen: set[str] = set()
    for source in sources:
        for item in source:
            term = str(item).strip()
            if term:
                seen.add(term)
    return tuple(sorted(seen))
