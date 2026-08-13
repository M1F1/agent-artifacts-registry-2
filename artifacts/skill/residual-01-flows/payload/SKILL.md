---
name: residual-01-flows
description: Map the actors in a system and every movement of information between them, as the stressable foundation for a residuality analysis. Use when running step 01 of a residual run.
---

# Step 01 — Flow analysis

## What you are producing

A list of **actors** and the **flows** between them. A flow is one movement of
information between two actors. An actor can be a person, a team, a company, or
a software component.

That is the whole definition. It is deliberately smaller than what you are used
to drawing.

## What a flow is not

Do not draw a process. Do not draw a use case. Do not draw a sequence of steps.

Decomposing a system along process lines is the specific mistake Parnas warned
about in 1971, and it is the one this step exists to avoid
(residuality-theory §flow-analysis). Once a process
diagram exists it shapes the architecture for the rest of the system's life, and
every later surprise gets absorbed as an "edge case" instead of being allowed to
break the abstraction.

Concretely:

- ✗ `1. customer requests charge → 2. system checks account → 3. system unlocks`
- ✓ `charger unit → session ingest : charge session telemetry (end of charge)`
- ✓ `pricing team → session ingest : tariff table (on change)`

## Procedure

1. **Gather context.** Use whatever tools this harness gives you — the
   capability list is in your work-unit prompt. Read the repository, the DAG or
   pipeline definitions, the docs, the lineage catalogue, the tickets. Record
   every tool you actually called in `tools_used`.

2. **List the actors first.** Include the ones with no code: the upstream team
   who owns a table, the analyst who exports to a spreadsheet, the regulator who
   receives a report, the vendor whose firmware writes the telemetry.

3. **For each pair of actors, ask what moves between them.** Name the
   information, not the mechanism. "billable session rows" tells you more than
   "POST /sessions".

4. **Record the trigger.** A schedule, an event, a request, a human deciding.
   The trigger is often where the stress will land later.

5. **Pay attention to boundaries.** The flows that cross a team or company
   boundary are the ones with implicit contracts, and implicit contracts are
   where architectures fail. If you find yourself writing "and then the finance
   team picks it up from there", that is a flow.

6. **Include the flows nobody designed.** A table someone queries directly. A
   CSV that became load-bearing. A dashboard a director reads every morning.
   These are real flows and they will be stressed later.

## Output

One JSON object per line, to the path named in your work-unit prompt:

```json
{"source": "...", "target": "...", "payload": "...", "trigger": "...", "notes": "...", "tools_used": ["..."]}
```

Do not assign `id` — identifiers are allocated deterministically at compile time.

## Why this matters downstream

The names you write here become the vocabulary that the stressor gate uses to
decide whether a stressor is grounded in *this* system or is generic filler. Use
the real names this business uses. If a thing has an internal nickname, that
nickname is more useful here than the formally correct term.

## Finishing

```bash
residual compile 01-flows && residual gate 01-flows
```

Then mark your unit done with the command in your prompt.

## Running this stage on its own

This stage reads nothing from the run, so it is the one you can always
start from: point it at a codebase and it produces the artifact every
later stage grounds itself in.

```bash
python skills/residual-01-flows/scripts/run.py plan      # expand this stage into work units
python skills/residual-01-flows/scripts/run.py next      # claim one and print its prompt
python skills/residual-01-flows/scripts/run.py compile   # merge the shards
python skills/residual-01-flows/scripts/run.py gate      # the deterministic checks
python skills/residual-01-flows/scripts/run.py report    # HTML, opens from file://
python skills/residual-01-flows/scripts/run.py test      # this stage's own tests
```

Same kernel and same run directory as `residual <command> 01-flows` — the stage
is implied rather than typed, so you cannot address another one by accident.

Everything this stage is made of lives in `skills/residual-01-flows/`: this file,
`step.py` (what it declares, compiles and gates), its runner, and its
own tests.
