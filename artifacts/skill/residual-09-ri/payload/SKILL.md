---
name: residual-09-ri
description: Judge, blind, whether each of two architectures survives each holdout stressor, producing the data for the residual index. Use when running step 09 of a residual run.
---

# Step 09 — The empirical test

## What you are producing

Two judgments per holdout stressor: does **Architecture A** survive it, and does
**Architecture B** survive it.

The kernel turns those into `Ri = (Y − X) / S`
(residuality-theory §empirical-test).

## You are not told which is which

Both architectures are in your prompt as flat component lists labelled A and B.
One is the naïve architecture, one is the residual one. The assignment comes from
a hash of the run slug, so it differs between runs.

**Do not try to work it out, and do not open the source files.** They are listed
as forbidden in your prompt. Judge each architecture on its own terms, in
isolation, as if the other did not exist.

You will notice that one list is longer. That is a real limitation of this test
and it is recorded as such — but a longer list is not a reason to be more
generous. A component that does not address the stressor does not help, and
extra components can make things worse.

## What "survives" means

The business moves into the attractor described by the stressor. Does this
architecture keep working there, or does it have to be rebuilt?

Survival is **not**:

- "it wouldn't crash"
- "you could add something to handle that"
- "with some changes it would be fine"

Survival **is**: something already in this architecture absorbs the change, and
you can name it and say how.

## The mechanism field is the discipline

Whenever you answer `survives: true`, you must name the specific component and
the specific way it absorbs the stressor. If you cannot write that sentence, the
answer is `false`.

This is not bookkeeping. An unfalsifiable yes is the failure mode of LLM
judging — the model wants to be agreeable, and "it would probably cope" scores
the same as real survival unless the format forces the difference. The gate
rejects a survival with no mechanism.

## Judge symmetrically

For each stressor, do A and B the same way:

1. read the stressor and its attractor
2. work down that architecture's component list
3. ask whether any of them, as described, absorbs it
4. write the judgment and the mechanism

Do not judge A, then judge B by comparison to A. Judge each against the stressor.

## Output

Two lines per stressor:

```json
{"stressor_id": "H0004", "arch": "A", "survives": false, "mechanism": ""}
{"stressor_id": "H0004", "arch": "B", "survives": true, "mechanism": "TariffVersionStore pins each settled row to the tariff version in force, so a retrospective edit cannot reprice it"}
```

## What the number means

```bash
residual compile 09-ri && residual gate 09-ri && residual ri
```

- **Ri > 0** — the analysis moved the architecture toward criticality
- **Ri = 0** — this round bought nothing measurable; further rounds have
  diminishing returns (residuality-theory §empirical-test)
- **Ri < 0** — either the added components brought their own fragility, or the
  judging is not reliable

Ri is a direction, not a grade. It is comparable only within one judge model and
one execution mode, and it says nothing about whether the architecture is
*good* — only whether this round of work improved its odds against stress nobody
predicted.

## Running this stage on its own

This stage is not self-sufficient: it reads artifacts earlier stages
produced.

- `02-naive/architecture.md` — from `02-naive`
- `05-architecture/components.csv` — from `05-architecture`
- `08-holdout/register.csv` — from `08-holdout`

Given those files in the run directory, nothing else about the pipeline has to
run, or even exist, for this stage to work.

```bash
python skills/residual-09-ri/scripts/run.py plan      # expand this stage into work units
python skills/residual-09-ri/scripts/run.py next      # claim one and print its prompt
python skills/residual-09-ri/scripts/run.py compile   # merge the shards
python skills/residual-09-ri/scripts/run.py gate      # the deterministic checks
python skills/residual-09-ri/scripts/run.py report    # HTML, opens from file://
python skills/residual-09-ri/scripts/run.py test      # this stage's own tests
```

Same kernel and same run directory as `residual <command> 09-ri` — the stage
is implied rather than typed, so you cannot address another one by accident.

Everything this stage is made of lives in `skills/residual-09-ri/`: this file,
`step.py` (what it declares, compiles and gates), its runner, and its
own tests.
