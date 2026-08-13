---
name: residual-04-residues
description: Turn one stressor into a concrete change to the architecture, or record that an earlier residue already survives it. Use when running step 04 of a residual run.
---

# Step 04 — Residue design

## What you are producing

For the stressor in your unit, **one** of two things:

1. a concrete change to the naïve architecture that survives that attractor, or
2. a note that residues written earlier already survive it.

The second outcome is not a failure. It is **looping**, and it is the result the
whole method is aiming at
(residuality-theory §looping-and-convergence).

## Read the other residues — this step is different

Step 03 forbade you from reading sibling shards, because generators that see
each other converge. **Step 04 requires the opposite.** The residues already
designed are summarised in your prompt. Use them:

- reuse their components rather than inventing a parallel one that does the same
  job under a different name;
- if one of them already absorbs your attractor, put its id in
  `already_survived_by` and leave `change` empty;
- if two of them combine to absorb it, list both. Combination is the second
  looping condition the book names
  (residuality-theory §looping-and-convergence).

## What makes a change concrete

Concrete means someone could disagree with it.

- ✗ "add validation", "improve monitoring", "make it more resilient"
- ✗ "introduce a queue" (which queue, between what, carrying what?)
- ✓ "pin each billable session row to the tariff version in force at read time,
  so a retrospective tariff edit cannot silently reprice settled sessions"

Name the components you are introducing or modifying. Those names go straight
into the contagion matrix as columns, so pick nouns you would be willing to
defend in an architecture review.

## The change follows the business reaction

Look at the stressor's `business_reaction` column before you design anything.
The technology serves whatever the business decided to do about the attractor;
inventing a technical answer to a problem the business solves with a policy is
how over-engineering starts. A residue with an empty `change` because the
business handled it socially is a perfectly good residue.

## A residue is not an implementation

You are describing what the architecture must be *able* to do, not committing to
build it. The book is explicit: a residue being present does not mean it gets
implemented (residuality-theory §cost-and-over-engineering).
The value is that the architecture is now primed to move there cheaply.

So do not filter on cost. Do not filter on likelihood. Those filters belong
after the architecture has been explored, not during.

## Output

```json
{
  "stressor_id": "S0007",
  "change": "...",
  "rationale": "why this and not another",
  "components": ["..."],
  "already_survived_by": ["R0003"],
  "tools_used": ["..."]
}
```

Leave `change` empty **only** when `already_survived_by` is populated. The gate
rejects a residue that is empty in both.

## Finishing

```bash
residual compile 04-residues && residual gate 04-residues
```

The gate reports the looping rate. Watch it across runs: a rate near zero means
there is more stressing to do; a rate that climbs and then plateaus is the
signal that the architecture is approaching criticality and further rounds will
buy less and less.

## Running this stage on its own

This stage is not self-sufficient: it reads artifacts earlier stages
produced.

- `02-naive/architecture.md` — from `02-naive`
- `03-stressors/register.csv` — from `03-stressors`

Given those files in the run directory, nothing else about the pipeline has to
run, or even exist, for this stage to work.

```bash
python skills/residual-04-residues/scripts/run.py plan      # expand this stage into work units
python skills/residual-04-residues/scripts/run.py next      # claim one and print its prompt
python skills/residual-04-residues/scripts/run.py compile   # merge the shards
python skills/residual-04-residues/scripts/run.py gate      # the deterministic checks
python skills/residual-04-residues/scripts/run.py report    # HTML, opens from file://
python skills/residual-04-residues/scripts/run.py test      # this stage's own tests
```

Same kernel and same run directory as `residual <command> 04-residues` — the stage
is implied rather than typed, so you cannot address another one by accident.

Everything this stage is made of lives in `skills/residual-04-residues/`: this file,
`step.py` (what it declares, compiles and gates), its runner, and its
own tests.
