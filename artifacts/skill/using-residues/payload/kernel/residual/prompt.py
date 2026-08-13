"""Rendering a work unit into a prompt a cold agent can execute.

This is the load-bearing piece of the restart loop. A prompt produced here has
to be executable by an agent with *no* conversation history: it names the files
to read, the provocation or records to work from, the exact output path and
schema, the gates the result must pass, and the command to run when finished.

The skeleton is here; the parts that differ per step come from the step's own
skill. A skill contributes three optional things:

``OUTPUT_SCHEMA``
    the JSON keys the agent must write, and nothing else;
``gate_rules(spec, config, profile)``
    what this unit will be judged on, in the agent's language;
``prompt_context(ctx, spec, unit)``
    the records, components or architectures the unit works from.

The isolation policy stays here, because it is a property of the pipeline
rather than of any one step, and because two opposite rules live in it that
quietly ruin the analysis if swapped: generation steps forbid reading sibling
shards, since generators that see each other converge (residuality-theory §random-simulation),
while residue design *requires* it, since noticing that an earlier residue
already covers this stressor is the looping measurement (residuality-theory §looping-and-convergence).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import config as config_mod
from . import registry
from .config import Config
from .model import BANNED_FIELDS, StepSpec, Unit
from .profiles import Profile
from .run import RunContext, raw_dir, resolve_input, shard_path

#: Shared by ``03-stressors`` and ``08-holdout``: they write the same record,
#: and a drift between the two would silently break the empirical test.
STRESSOR_SCHEMA = """{
  "stressor": "what could happen, told as a specific story about THIS system",
  "detection": "how this business would first notice it -- an alarm, a report, a phone call",
  "attractor": "the state the business settles into once it has happened",
  "business_reaction": "what the business does about it, technology aside",
  "technical_change": "the change to the naive architecture that survives it (may be empty)",
  "components_touched": ["component names from the naive architecture"],
  "tools_used": ["names of any context tools you actually called"]
}"""

DEFAULT_GATE_RULES = "- every field non-empty except those marked optional"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def capability_block(spec: StepSpec, config: Config) -> str:
    if not spec.capabilities:
        return "_This step needs no external context tools._"

    lines: list[str] = []
    for capability in spec.capabilities:
        tools = config_mod.tools_for(config, capability)
        rendered = ", ".join(f"`{t}`" for t in tools) if tools else "_unbound_"
        lines.append(f"- `{capability}` -> {rendered}")

    return "\n".join(
        [
            *lines,
            "",
            "Unbound capabilities are not an error. Use whatever tools this "
            "harness actually offers that could serve them, and list every tool "
            "you called in `tools_used` so the provenance stays honest.",
        ]
    )


def stressor_gate_rules(spec: StepSpec, config: Config, profile: Profile) -> str:
    """What a stressor unit is judged on. Used by both stressor-writing steps."""
    minimum = config_mod.gate(config, "min_records_per_shard", spec.id)
    specificity = config_mod.gate(config, "min_specificity", spec.id)
    quota = config_mod.gate(config, "technical_quota", spec.id)
    return "\n".join(
        [
            f"- at least **{minimum} records**; there is no upper limit",
            f"- each `stressor` names at least **{specificity}** thing that actually "
            "exists in this system -- a real component, actor, dataset, team or "
            "flow. A stressor that would read identically at any other company "
            "fails this gate.",
            "- no record may be a restatement of the provocation below. The "
            "provocation is a question; your record is a specific answer about "
            "this system.",
            f"- at most **{int(float(quota) * 100)}%** of records may be "
            "infrastructure-flavoured. Heavily technical stressor lists are a "
            "warning sign (residuality-theory §technical-skew) -- the interesting stress comes "
            "from the business, the market, regulation and people.",
            "- no probability, no impact score, no cost, no priority. These keys "
            f"are rejected outright: {', '.join(BANNED_FIELDS)}.",
        ]
    )


def gate_block(spec: StepSpec, config: Config, profile: Profile) -> str:
    rules = registry.hook(spec.id, "gate_rules")
    if rules is None:
        return DEFAULT_GATE_RULES
    return rules(spec, config, profile) if callable(rules) else str(rules)


def isolation_block(ctx: RunContext, spec: StepSpec, unit: Unit) -> str:
    parts: list[str] = []

    if spec.siblings == "forbidden":
        directory = rel(raw_dir(ctx, spec))
        mine = rel(shard_path(ctx, spec, unit.shard))
        parts.append(
            f"Do **not** read anything else in `{directory}/`. Other shards' "
            "output is sitting there, and reading it makes your answers converge "
            f"on theirs -- which defeats the whole method. Your file is `{mine}` "
            "and nothing else in that directory concerns you."
        )
    elif spec.siblings == "required":
        parts.append(
            "Unlike the stressor step, you **should** look at what the other "
            "residues have already decided — it is summarised below. Reuse their "
            "components rather than inventing parallel ones, and if one of them "
            "already survives your attractor, say so instead of designing again."
        )

    if spec.forbidden_summary:
        parts.append(spec.forbidden_summary)
    elif spec.forbidden_paths:
        listed = "\n".join(f"- `{path}`" for path in spec.forbidden_paths)
        parts.append(
            "You must **not** open these files. Everything you need from them is "
            f"already in this prompt, and reading them would invalidate the "
            f"result this step exists to produce:\n\n{listed}"
        )

    return "\n\n".join(parts)


# --------------------------------------------------------------------------
# helpers the skills build their context blocks from
# --------------------------------------------------------------------------

_BULLET = re.compile(r"^\s*[-*]\s+(.*\S)\s*$")


def plain(value: str) -> str:
    """Strip markdown emphasis so two documents read in one voice.

    The naïve architecture arrives as hand-written markdown and the residual one
    as compiled records. Left alone, one list would come out backticked and the
    other bare -- a stylistic tell that would undo the blinding just as surely as
    a label.
    """
    return " ".join(value.replace("`", "").replace("**", "").replace("*", "").split())


def components_from_markdown(body: str) -> tuple[str, ...]:
    """Bullets under a `## Components` heading, for normalising the naïve doc."""
    out: list[str] = []
    inside = False
    for line in body.splitlines():
        if line.strip().lower().startswith("## "):
            inside = "component" in line.lower()
            continue
        if inside:
            match = _BULLET.match(line)
            if match:
                out.append(plain(match.group(1)))
    return tuple(out)


def rows_table(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    if not rows:
        return "_No rows in this batch._"
    blocks: list[str] = []
    for row in rows:
        lines = [f"### `{row.get('id', '?')}`"]
        lines += [
            f"- **{field.replace('_', ' ')}**: {row[field]}"
            for field in fields
            if row.get(field)
        ]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def step_context(ctx: RunContext, spec: StepSpec, unit: Unit) -> str:
    """Whatever this step's skill wants the agent to have in front of it."""
    build = registry.hook(spec.id, "prompt_context")
    if build is not None:
        return build(ctx, spec, unit)

    rows = list(unit.payload.get("rows") or [])
    if rows:
        return "\n\n".join(
            ["## Records in this batch", rows_table(rows, ("stressor", "attractor"))]
        )
    return ""


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------


def render(
    unit: Unit,
    spec: StepSpec,
    ctx: RunContext,
    config: Config,
    profile: Profile,
) -> str:
    output = shard_path(ctx, spec, unit.shard)
    forbidden = set(spec.forbidden_paths)
    inputs = [rel(resolve_input(ctx, p)) for p in spec.inputs if p not in forbidden]
    schema = str(registry.hook(spec.id, "OUTPUT_SCHEMA", "") or "")

    sections: list[str] = [
        f"# Work unit `{unit.id}`",
        "",
        "You are executing one unit of a residuality analysis. Everything you "
        "need is in this prompt; you are not expected to have any prior "
        "conversation, and you should not ask for one.",
        "",
        f"## Step: {spec.title}",
        "",
        spec.goal,
        "",
        f"The full procedure is in `{spec.skill}` — read it before you start.",
        "",
    ]

    if inputs:
        sections += ["## Read these first", "", *[f"- `{p}`" for p in inputs], ""]

    if unit.payload.get("provoke"):
        sections += [
            "## Your lens",
            "",
            f"- id: `{unit.payload.get('lens', unit.shard)}`",
            f"- kind: `{unit.payload.get('kind', 'domain')}`",
            "",
            "> " + str(unit.payload["provoke"]).replace("\n", "\n> "),
            "",
            "This is a question, not a template. Answer it about this system.",
            "",
        ]

    context = step_context(ctx, spec, unit)
    if context:
        sections += [context, ""]

    sections += ["## Context tools", "", capability_block(spec, config), "", "## Output", ""]

    if spec.record_type == "document":
        sections += [f"Write markdown to `{rel(output)}`.", ""]
    else:
        sections += [
            f"Write one JSON object per line to `{rel(output)}`.",
            "",
            "Exactly these keys, no others:",
            "",
            "```json",
            schema,
            "```",
            "",
            "Do not invent an `id` field. Identifiers are assigned "
            "deterministically when the shards are compiled, so that a parallel "
            "run and a sequential run produce the same register.",
            "",
        ]

    isolation = isolation_block(ctx, spec, unit)
    if isolation:
        sections += [isolation, ""]

    sections += [
        "## Gates this unit must pass",
        "",
        gate_block(spec, config, profile),
        "",
        "## When you are finished",
        "",
        "```bash",
        f"residual done {unit.id}",
        "```",
        "",
        "If you genuinely cannot complete it, say why and run:",
        "",
        "```bash",
        f'residual fail {unit.id} "<reason>"',
        "```",
        "",
    ]

    if profile.names:
        sections += [f"_Profile: {', '.join(profile.names)}._", ""]

    return "\n".join(sections)
