---
name: residual-08-holdout
description: Generate a fresh set of stressors that has never seen the residues, as the test set for the empirical test. Use when running step 08 of a residual run.
---

# Step 08 — Holdout stressors

## What you are producing

Stressors, exactly as in step 03 — same chain, same rules, same schema.

With one difference that is the entire point of the step.

## You must not know what was designed

These stressors are the **test set**. They exist to be applied to two
architectures that have already been built, and the whole result depends on them
having played no part in building either
(residuality-theory §empirical-test).

So you must not open:

- `03-stressors/register.csv` — the training stressors
- `04-residues/residues.csv` — the residues
- `05-architecture/components.csv` — the residual architecture
- `07-review/review.md`

Your prompt does not name them and does not need them. You have the flows, and
that is deliberate: the flows describe the system, the residues describe the
answer, and a test set that has seen the answer measures nothing.

If you find yourself thinking "the architecture probably handles X, so let me
stress Y instead" — stop. That thought means you are reasoning about a design you
should not be able to see.

**Do not read sibling shards either**, for the same reason as step 03.

## Why a human cannot do this properly

An architect who has just spent a week designing residues cannot unsee them.
Their "fresh" stressors will be shaped by what they know the architecture covers,
in both directions — avoiding what it handles, or unconsciously testing what they
are proud of. This is not a character flaw; it is unavoidable.

A cold agent that has genuinely never seen the residues has no such bias. That is
one of the few places where running this with agents is not merely faster but
methodologically better than doing it by hand — and it is only true if you honour
the isolation.

## Everything else is step 03

Read [`skills/residual-03-stressors/SKILL.md`](../03-stressors/SKILL.md) for the chain,
the rules and what a good row looks like. Same lens, same specificity
requirement, same ban on probability and cost.

## The one extra gate

Your rows are checked for **leakage**: a holdout stressor that restates a
training stressor inflates the result without the architecture having earned
anything. The check is lexical, so it catches copies and rewordings but not two
stressors that mean the same thing in different words — which is another reason
not to go looking at the training set.

## Finishing

```bash
residual compile 08-holdout && residual gate 08-holdout
```

## Running this stage on its own

This stage is not self-sufficient: it reads artifacts earlier stages
produced.

- `01-flows/flows.csv` — from `01-flows`

Given those files in the run directory, nothing else about the pipeline has to
run, or even exist, for this stage to work.

```bash
python skills/residual-08-holdout/scripts/run.py plan      # expand this stage into work units
python skills/residual-08-holdout/scripts/run.py next      # claim one and print its prompt
python skills/residual-08-holdout/scripts/run.py compile   # merge the shards
python skills/residual-08-holdout/scripts/run.py gate      # the deterministic checks
python skills/residual-08-holdout/scripts/run.py report    # HTML, opens from file://
python skills/residual-08-holdout/scripts/run.py test      # this stage's own tests
```

Same kernel and same run directory as `residual <command> 08-holdout` — the stage
is implied rather than typed, so you cannot address another one by accident.

Everything this stage is made of lives in `skills/residual-08-holdout/`: this file,
`step.py` (what it declares, compiles and gates), its runner, and its
own tests.
