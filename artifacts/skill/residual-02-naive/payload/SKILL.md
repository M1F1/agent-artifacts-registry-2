---
name: residual-02-naive
description: Write the deliberately unimaginative starting architecture that solves the stated problem, to serve as the control arm of a residuality analysis. Use when running step 02 of a residual run.
---

# Step 02 — The naïve architecture

## What you are producing

The smallest architecture that solves the problem **exactly as it has been
stated**, and nothing more.

## This is meant to be unimpressive

Your instinct will be to make it good. Resist it.

The naïve architecture has two jobs, and being a good architecture is neither of
them:

1. It is the thing that gets stressed in step 03. Every residue is described as
   a *change* to this, so it has to be simple enough that changes are legible.
2. It is the **control arm** of the empirical test. Later, both this and the
   residual architecture are scored against a fresh set of stressors, and the
   difference between them is the whole result
   (residuality-theory §empirical-test). If you smuggle
   robustness in here, you destroy the measurement — and you will not be able to
   tell afterwards whether the analysis achieved anything.

The book is blunt that the starting point is arbitrary
(residuality-theory §naive-architecture). Take it
literally.

## Rules

- **Do not anticipate stress.** No redundancy you were not asked for, no
  retries, no queues "for resilience", no feature flags, no extension points.
- **Do not apply patterns because they are good practice.** If you find yourself
  reaching for a pattern, that is a signal to write the boring version and let
  step 03 justify the pattern — or fail to.
- **Do not solve problems the flows have not shown you.**
- **Name every component explicitly.** These names become the columns of the
  contagion matrix later, so they must be nouns you can point at.

## Procedure

1. Read `01-flows/flows.csv`. That is the problem statement.
2. Write the simplest structure that carries those flows.
3. List its components as a flat, named list.
4. State the assumptions you are making. Every assumption is a target for step
   03 — this list is a gift to your later self.

## Output

Markdown, to the path named in your work-unit prompt. Structure it as:

```markdown
# Naïve architecture

## Components
- `name` — one line on what it does

## How the flows are carried
(one line per flow from flows.csv)

## Assumptions
- ...
```

## A note on the assumptions section

Write the assumptions you would normally leave unwritten because they are
obvious. "A customer is a person." "Sessions arrive once." "The tariff is a
number." Those obvious ones are exactly the abstractions that tear architectures
apart (residuality-theory §edge-cases-and-abstractions), and the
concept-collapse lens in step 03 will go looking for them.

## Finishing

```bash
residual compile 02-naive && residual gate 02-naive
```

## Running this stage on its own

This stage is not self-sufficient: it reads artifacts earlier stages
produced.

- `01-flows/flows.csv` — from `01-flows`

Given those files in the run directory, nothing else about the pipeline has to
run, or even exist, for this stage to work.

```bash
python skills/residual-02-naive/scripts/run.py plan      # expand this stage into work units
python skills/residual-02-naive/scripts/run.py next      # claim one and print its prompt
python skills/residual-02-naive/scripts/run.py compile   # merge the shards
python skills/residual-02-naive/scripts/run.py gate      # the deterministic checks
python skills/residual-02-naive/scripts/run.py report    # HTML, opens from file://
python skills/residual-02-naive/scripts/run.py test      # this stage's own tests
```

Same kernel and same run directory as `residual <command> 02-naive` — the stage
is implied rather than typed, so you cannot address another one by accident.

Everything this stage is made of lives in `skills/residual-02-naive/`: this file,
`step.py` (what it declares, compiles and gates), its runner, and its
own tests.
