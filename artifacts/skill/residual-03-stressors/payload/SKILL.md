---
name: residual-03-stressors
description: Generate stressors for one lens — randomly simulating the business environment to find the attractors an architecture must survive. Use when running step 03 of a residual run.
---

# Step 03 — Stressor analysis

## What a stressor is

**A stressor is any fact about the context that is currently outside your
understanding of the system.**

Not a risk. Not a requirement. Not an edge case. Not a failure mode.

It does not need to be likely. It does not need consensus. It does not need a
probability, and you must not give it one. It needs exactly one thing: a
coherent story about how the business ends up somewhere different
(residuality-theory §stressors).

## The chain you are writing

Every row is one residue, and it follows one chain:

```
stressor  →  detection  →  attractor  →  business reaction  →  technical change
```

- **stressor** — what happens, as a specific story about this system
- **detection** — how this business first *notices*. An alarm, a report, an
  angry phone call, a number that looks wrong. This column matters more than it
  looks: how you detect something usually dictates what you have to build.
- **attractor** — the state the business settles into afterwards. Not the
  incident; the new normal. This is the part people skip, and it is the part
  that carries all the value.
- **business reaction** — what the business does about it, technology aside.
  Sometimes the answer is a policy, a price change, or a new team. That is a
  legitimate outcome — not everything is solved with software
  (residuality-theory §residues).
- **technical change** — the change to the naïve architecture that survives the
  attractor. **May be empty.** Plenty of good stressors touch no code, and the
  conversation is still worth having.

## Working your lens

Your work-unit prompt contains one lens: a provocation. It is a question, not a
template. Read it, then:

1. **Read the flows and the naïve architecture.** Everything you write must be
   about the system described there.
2. **Pick something concrete** from that system — a specific flow, actor, table,
   assumption or noun — and let the provocation act on *that thing*.
3. **Tell the story forward.** Do not stop at the moment of impact. Ask "and
   then what?" three or four times until the business has settled somewhere.
   That settled place is the attractor.
4. **Only then** ask what the architecture would have to be for that to be
   survivable.
5. Go back to step 2 with a different concrete thing. Keep going until you run
   dry, then push through once more — the fourth and fifth are usually better
   than the first.

## Rules

- **No probability, no impact, no cost, no priority.** These are banned outright
  and the gate rejects records carrying them
  (residuality-theory §stressors). Cost-thinking
  filters the simulation exactly the way probability does, and it filters out
  precisely the interesting rows.
- **Nothing may be generic.** If your stressor would read identically in another
  company's analysis, it is filler. Name the real table, the real team, the real
  product. The gate measures this.
- **Do not restate the provocation.** It is a question. Your answer is specific.
  The gate measures this too.
- **Break abstractions, do not extend them.** When a noun stops fitting, the
  answer is not a new optional field. It is that the noun was two things all
  along (residuality-theory §edge-cases-and-abstractions).
- **Stay out of the machine room.** A list dominated by servers, memory and
  deploys means the walk never left the building
  (residuality-theory §technical-skew). The
  quota is enforced. The interesting stress comes from markets, regulation,
  people and money.
- **Do not read the other shards.** They are on disk next to yours. Reading them
  makes your answers converge on theirs, which is the one failure mode this
  whole method exists to prevent
  (residuality-theory §random-simulation).

## The shape of a good row

This is from the book's own worked example — a different domain on purpose.
**Copy the shape, never the content.** A shipped stressor list is the generic
pattern trap (residuality-theory §stressors).

| field | value |
| --- | --- |
| stressor | Customers park at a charger and leave the car there all day |
| detection | Licence-plate cameras; queue complaints |
| attractor | Chargers are occupied but not earning; subscribers churn to competitors |
| business reaction | Move from per-charge pricing to time-based billing on a sliding scale |
| technical change | Billing runs after the customer leaves the bay, not at end of charge; status polled continuously |

Note what makes it good: it is specific to that business, the attractor is a
*business state* rather than an outage, the business reaction is a pricing
decision, and the technical change falls out of the reaction rather than leading
it.

## How many

As many as the lens honestly yields — the gate expects at least eight per shard
and there is no upper limit. A full analysis across all lenses should reach a
few hundred rows
(residuality-theory §stressors).

Quantity is not padding here. The leverage of the whole method is that many
stressors lead to the same attractor, so finding one protects you against all
the ones you never thought of
(residuality-theory §attractors).

## When the analysis is finished

Not your problem for a single unit, but worth knowing what you are contributing
to: the analysis is done when new stressors keep turning out to be **already
survived** by residues from earlier lenses. That looping is the signal the
architecture is approaching criticality
(residuality-theory §looping-and-convergence) — and it is the
reason the queue terminates on convergence rather than on a budget.

## Output

One JSON object per line, to the path in your work-unit prompt:

```json
{
  "stressor": "...",
  "detection": "...",
  "attractor": "...",
  "business_reaction": "...",
  "technical_change": "...",
  "components_touched": ["..."],
  "tools_used": ["..."]
}
```

No `id` — identifiers are assigned deterministically at compile time so that a
parallel run and a sequential run produce the same register.

## Finishing

```bash
residual compile 03-stressors && residual gate 03-stressors && residual report 03-stressors
```

If the gate rejects your unit, fix the rows rather than arguing with the
threshold. The gate is deliberately dumber than you are; it is there to catch
the failure modes that are invisible from inside the context that produced them.

## Running this stage on its own

This stage is not self-sufficient: it reads artifacts earlier stages
produced.

- `01-flows/flows.csv` — from `01-flows`
- `02-naive/architecture.md` — from `02-naive`

Given those files in the run directory, nothing else about the pipeline has to
run, or even exist, for this stage to work.

```bash
python skills/residual-03-stressors/scripts/run.py plan      # expand this stage into work units
python skills/residual-03-stressors/scripts/run.py next      # claim one and print its prompt
python skills/residual-03-stressors/scripts/run.py compile   # merge the shards
python skills/residual-03-stressors/scripts/run.py gate      # the deterministic checks
python skills/residual-03-stressors/scripts/run.py report    # HTML, opens from file://
python skills/residual-03-stressors/scripts/run.py test      # this stage's own tests
```

Same kernel and same run directory as `residual <command> 03-stressors` — the stage
is implied rather than typed, so you cannot address another one by accident.

Everything this stage is made of lives in `skills/residual-03-stressors/`: this file,
`step.py` (what it declares, compiles and gates), its runner, and its
own tests.
