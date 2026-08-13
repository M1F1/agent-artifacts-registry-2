---
name: residual-06-matrix
description: Fill the contagion matrix — which components each stressor reaches — so the seven refactoring triggers can be computed. Use when running step 06 of a residual run.
---

# Step 06 — Contagion analysis

## What you are producing

For each stressor in your batch, the list of components it **reaches**. That is
the whole task. The arithmetic — row totals, column totals, coupling, merge
candidates — is computed by the kernel afterwards, so you never have to count
anything.

## What "reaches" means

A stressor reaches a component if, when that stressor happens, that component's
operation is affected: it has to change, it behaves differently, it produces
something wrong, or it becomes the thing everyone depends on.

It is not "is this component mentioned in the residue". It is "would this
component be disturbed".

Be honest in both directions. Marking everything makes the matrix useless; so
does marking only the obvious one.

## What this matrix is not

It is not a domain map. Traditional methods map components to business concepts;
this maps components against the **frictions that appear as the business
changes** — relationships across the hyperliminal boundary
(residuality-theory §contagion-analysis).

You are not drawing dependencies. Two components with no functional connection
whatsoever can share a row, and that is the single most valuable thing this
matrix produces.

## Rules

- Use component names **exactly** as they appear in the list in your prompt.
  A name that does not match is dropped and fails the gate rather than quietly
  creating a new column.
- Every stressor in your batch needs a row, even if `hits` is empty. An empty row
  is a real answer: some stressors are handled entirely by the business.
- Do not consult the other batches. Consistency comes from the component list,
  which everyone shares.

## Output

```json
{"stressor_id": "S0007", "hits": ["TariffVersionStore", "SettlementLedger"], "note": ""}
```

## What happens next

The kernel computes the seven triggers
(residuality-theory §contagion-analysis) and renders them:

1. **hot rows** — stressors with the widest blast radius; where hyperliminal
   coupling and the elusive non-functional concerns live
2. **hot columns** — components most sensitive to stress; either doing too much,
   or genuinely central and in need of redundancy
3. **two 1s in a row** — coupling; if the pair has no functional dependency, it
   is the invisible kind
4. **identical column signatures** — components that live and die together, so
   they can be merged and N lowered
5. **many high numbers** — K is too high; the architecture may need rebuilding
6. **stressor combinations** — what a second stressor would do to an already
   damaged system
7. **untouched columns** — almost always a sign you have not stressed that part
   enough, not that it is invulnerable

These are prompts for an argument. The book is explicit that this could be run
as a mechanical algorithm but that the value is in the conversations it triggers
(residuality-theory §the-artifacts) — so read the
report with the people who own these components, and expect to go back and
refactor step 05.

## Finishing

```bash
residual compile 06-matrix && residual gate 06-matrix && residual report 06-matrix
```

## Running this stage on its own

This stage is not self-sufficient: it reads artifacts earlier stages
produced.

- `03-stressors/register.csv` — from `03-stressors`
- `05-architecture/components.csv` — from `05-architecture`

Given those files in the run directory, nothing else about the pipeline has to
run, or even exist, for this stage to work.

```bash
python skills/residual-06-matrix/scripts/run.py plan      # expand this stage into work units
python skills/residual-06-matrix/scripts/run.py next      # claim one and print its prompt
python skills/residual-06-matrix/scripts/run.py compile   # merge the shards
python skills/residual-06-matrix/scripts/run.py gate      # the deterministic checks
python skills/residual-06-matrix/scripts/run.py report    # HTML, opens from file://
python skills/residual-06-matrix/scripts/run.py test      # this stage's own tests
```

Same kernel and same run directory as `residual <command> 06-matrix` — the stage
is implied rather than typed, so you cannot address another one by accident.

Everything this stage is made of lives in `skills/residual-06-matrix/`: this file,
`step.py` (what it declares, compiles and gates), its runner, and its
own tests.
