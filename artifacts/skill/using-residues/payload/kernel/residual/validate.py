"""The gate kit: deterministic checks a step's skill composes into its gate.

No model judgment happens here, and nothing in this module reads the network or
the clock. Gates are the reason artifacts produced by three different harnesses
are comparable at all: the agent supplies the imagination, the gate supplies the
standard.

Each step's gate lives in its own skill, because what makes a *residue* good is
not what makes a *judgment* good. What lives here is the machinery more than one
step needs: the vocabulary a stressor has to be grounded in, the similarity
checks, the shared stressor gate that both ``03-stressors`` and ``08-holdout``
run, and the document gate that ``02-naive`` and ``07-review`` share.

Every similarity figure comes from :mod:`residual.text`, which is lexical. Two
stressors that mean the same thing in different words will pass the duplicate
gate, so redundancy counts are reported as a lower bound rather than a verdict.
"""

from __future__ import annotations

from collections import Counter
from typing import Mapping, Sequence

from . import config as config_mod
from . import fs, merge, registry, text
from .config import Config
from .model import (
    GateResult,
    Issue,
    StepSpec,
    Stressor,
    banned_fields_present,
)
from .profiles import Profile, all_lenses
from .run import RunContext, compiled_path, resolve_input

REQUIRED_STRESSOR_FIELDS: tuple[str, ...] = (
    "stressor",
    "detection",
    "attractor",
    "business_reaction",
)

DEFAULT_TECHNICAL_MARKERS: tuple[str, ...] = (
    "server",
    "database",
    "disk",
    "memory",
    "cpu",
    "timeout",
    "deploy",
    "cache",
    "latency",
    "container",
    "certificate",
    "api gateway",
)


def vocabulary(ctx: RunContext, profile: Profile) -> tuple[str, ...]:
    """The terms that make a stressor specific to *this* system.

    Deliberately built from the flows this analysis actually discovered, plus
    whatever a workplace profile overlay names explicitly. Technology vocabulary
    is left out on purpose: if ``dag`` or ``dataset`` counted as specific, then
    "a DAG fails" would pass the gate, and that sentence is true of every data
    platform ever built.

    Both whole names and their individual words count, so a flow payload of
    "settlement ledger export" grounds a stressor that only mentions the ledger.
    """
    terms: list[str] = list(profile.vocabulary)

    flows_path = resolve_input(ctx, "01-flows/flows.csv")
    for row in fs.read_csv(flows_path):
        terms += [row.get("source", ""), row.get("target", ""), row.get("payload", "")]

    expanded: list[str] = []
    for term in terms:
        cleaned = str(term).strip()
        if not cleaned:
            continue
        expanded.append(cleaned)
        expanded.extend(word for word in text.tokens(cleaned) if len(word) > 3)

    return text.vocabulary_from(expanded)


def lens_provocations(profile: Profile) -> Mapping[str, str]:
    return {lens.id: lens.provoke for lens in all_lenses(profile)}


# --------------------------------------------------------------------------
# individual checks
# --------------------------------------------------------------------------


def banned_field_issues(ctx: RunContext, spec: StepSpec) -> tuple[Issue, ...]:
    """Banned scoring fields, checked against raw shards.

    Compiled records have already dropped unknown keys, so this has to look at
    what the agent actually wrote.
    """
    issues: list[Issue] = []
    for shard, record in merge.read_shards(ctx, spec):
        banned = banned_fields_present(record)
        if banned:
            issues.append(
                Issue(
                    code="banned-field",
                    detail=(
                        f"record carries {', '.join(banned)}. Residuality admits "
                        "no probability, impact or cost during the simulation "
                        "(residuality-theory §stressors)."
                    ),
                    where=shard,
                )
            )
    return tuple(issues)


def missing_field_issues(stressors: Sequence[Stressor]) -> tuple[Issue, ...]:
    issues: list[Issue] = []
    for s in stressors:
        empty = [
            name
            for name in REQUIRED_STRESSOR_FIELDS
            if not str(getattr(s, name, "")).strip()
        ]
        if empty:
            issues.append(
                Issue(
                    code="empty-field",
                    detail=f"missing {', '.join(empty)}",
                    where=s.id,
                )
            )
    return tuple(issues)


def specificity_issues(
    stressors: Sequence[Stressor], vocab: Sequence[str], minimum: int
) -> tuple[Issue, ...]:
    if not vocab:
        return (
            Issue(
                code="no-vocabulary",
                detail=(
                    "no domain vocabulary available, so the specificity gate is "
                    "inert. Run 01-flows first, or give the profile a "
                    "`vocabulary` list."
                ),
                severity="warning",
            ),
        )
    issues: list[Issue] = []
    for s in stressors:
        hits = text.specificity(f"{s.stressor} {s.attractor}", vocab)
        if hits < minimum:
            issues.append(
                Issue(
                    code="generic-stressor",
                    detail=(
                        f"names {hits} term(s) from this system; needs {minimum}. "
                        "A stressor that would read identically at another "
                        "company is generic by construction."
                    ),
                    where=s.id,
                )
            )
    return tuple(issues)


def paraphrase_issues(
    stressors: Sequence[Stressor], provocations: Mapping[str, str], threshold: float
) -> tuple[Issue, ...]:
    issues: list[Issue] = []
    for s in stressors:
        provoke = provocations.get(s.lens)
        if not provoke:
            continue
        score = text.similarity(s.stressor, provoke)
        if score >= threshold:
            issues.append(
                Issue(
                    code="lens-paraphrase",
                    detail=(
                        f"similarity {score:.2f} to its own lens provocation "
                        f"(limit {threshold:.2f}) -- this restates the question "
                        "instead of answering it about this system."
                    ),
                    where=s.id,
                )
            )
    return tuple(issues)


def duplicate_issues(
    stressors: Sequence[Stressor], threshold: float
) -> tuple[Issue, ...]:
    pairs = text.near_duplicates([s.stressor for s in stressors], threshold)
    return tuple(
        Issue(
            code="near-duplicate",
            detail=(
                f"{stressors[i].id} and {stressors[j].id} score {score:.2f} "
                f"(limit {threshold:.2f}); keep the more specific one."
            ),
            where=f"{stressors[i].id}+{stressors[j].id}",
            severity="warning",
        )
        for i, j, score in pairs
    )


def technical_share(
    stressors: Sequence[Stressor], markers: Sequence[str]
) -> tuple[float, tuple[str, ...]]:
    flagged = tuple(
        s.id
        for s in stressors
        if text.marker_hits(f"{s.stressor} {s.attractor}", markers)
    )
    share = len(flagged) / len(stressors) if stressors else 0.0
    return share, flagged


def shard_size_issues(
    ctx: RunContext, spec: StepSpec, minimum: int
) -> tuple[Issue, ...]:
    tally = Counter(shard for shard, _ in merge.read_shards(ctx, spec))
    return tuple(
        Issue(
            code="thin-shard",
            detail=f"{count} record(s), expected at least {minimum}",
            where=shard,
            severity="warning",
        )
        for shard, count in sorted(tally.items())
        if count < minimum
    )


def leaked(
    holdout: Sequence[Stressor],
    training: Sequence[Stressor],
    threshold: float,
) -> tuple[tuple[str, str, float], ...]:
    """Holdout rows that are restatements of training rows.

    A contaminated holdout inflates Y without the architecture having earned it.
    Lexical only, so this is a floor: it catches copies and rewordings, not two
    stressors that mean the same thing in different vocabulary.
    """
    out: list[tuple[str, str, float]] = []
    for candidate in holdout:
        for known in training:
            score = text.similarity(candidate.stressor, known.stressor)
            if score >= threshold:
                out.append((candidate.id, known.id, round(score, 4)))
    return tuple(sorted(out, key=lambda item: (-item[2], item[0], item[1])))


# --------------------------------------------------------------------------
# gates shared by more than one step
# --------------------------------------------------------------------------


def stressor_gate(
    ctx: RunContext, spec: StepSpec, config: Config, profile: Profile
) -> GateResult:
    """The gate both stressor-generating steps run.

    ``08-holdout`` adds leak detection on top; everything else about judging a
    stressor register is identical, and duplicating it would let the two drift.
    """
    stressors = merge.load_stressors(ctx, spec)
    vocab = vocabulary(ctx, profile)
    # Profile markers add to the defaults rather than replacing them: a profile
    # names the machine-room concerns peculiar to its technology, but "the
    # server goes down" is the lazy technical stressor everywhere.
    markers = text.vocabulary_from(profile.technical_markers, DEFAULT_TECHNICAL_MARKERS)

    min_specificity = int(config_mod.gate(config, "min_specificity", spec.id))
    dup_threshold = float(config_mod.gate(config, "duplicate_threshold", spec.id))
    para_threshold = float(config_mod.gate(config, "paraphrase_threshold", spec.id))
    quota = float(config_mod.gate(config, "technical_quota", spec.id))
    min_records = int(config_mod.gate(config, "min_records_per_shard", spec.id))

    issues: list[Issue] = []
    if not stressors:
        issues.append(
            Issue(code="empty-register", detail="no stressors compiled for this step")
        )

    issues += list(banned_field_issues(ctx, spec))
    issues += list(missing_field_issues(stressors))
    issues += list(specificity_issues(stressors, vocab, min_specificity))
    issues += list(paraphrase_issues(stressors, lens_provocations(profile), para_threshold))
    issues += list(duplicate_issues(stressors, dup_threshold))
    issues += list(shard_size_issues(ctx, spec, min_records))

    share, flagged = technical_share(stressors, markers)
    if share > quota:
        issues.append(
            Issue(
                code="technical-skew",
                detail=(
                    f"{share:.0%} of stressors are infrastructure-flavoured "
                    f"(limit {quota:.0%}). A very technical list means the "
                    "simulation never left the machine room "
                    "(residuality-theory §technical-skew)."
                ),
            )
        )

    by_lens = Counter(s.lens for s in stressors)
    blind = sum(1 for s in stressors if s.provenance.blind)
    stats = {
        "records": len(stressors),
        "lenses": len(by_lens),
        "per_lens": dict(sorted(by_lens.items())),
        "technical_share": round(share, 4),
        "technical_flagged": list(flagged),
        "blind_records": blind,
        "blind_share": round(blind / len(stressors), 4) if stressors else 0.0,
        "duplicate_pairs": sum(1 for i in issues if i.code == "near-duplicate"),
        "duplicate_note": "lexical only; semantically equivalent rows are not detected",
        "vocabulary_terms": len(vocab),
    }
    return GateResult(step=spec.id, issues=tuple(issues), stats=stats)


def document_gate(ctx: RunContext, spec: StepSpec) -> GateResult:
    """For steps whose output is prose: it exists and is not empty.

    Deliberately thin. A deterministic check cannot tell whether an architecture
    document is any good, and pretending otherwise would put a number on
    something only a reader can judge.
    """
    path = compiled_path(ctx, spec)
    body = fs.read_text(path).strip() if path.exists() else ""
    issues = (
        ()
        if body
        else (Issue(code="empty-document", detail=f"{path} is empty"),)
    )
    return GateResult(step=spec.id, issues=issues, stats={"characters": len(body)})


# --------------------------------------------------------------------------
# dispatch
# --------------------------------------------------------------------------


def run(
    ctx: RunContext, spec: StepSpec, config: Config, profile: Profile
) -> GateResult:
    """Gate a step by asking its skill to do it."""
    return registry.call(spec.id, "gate", ctx, spec, config, profile)
