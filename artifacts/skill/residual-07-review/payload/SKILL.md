---
name: residual-07-review
description: Run FMEA and ATAM over the candidate residual architecture to catch technical failure modes and stakeholder trade-offs the earlier steps introduced. Use when running step 07 of a residual run.
---

# Step 07 — FMEA and ATAM review

## Why this step exists

Every step in this process is a safety net for the one before it
(residuality-theory §safety-nets). Steps 03–06 added
components to survive stress. This step asks what those *additions* broke.

This is where the analogy with traditional engineering is actually resonant.
Once the random simulation is done, systems engineering comes back into play:
making the structure behave the way it was intended to
(residuality-theory §fmea-atam).

## Part 1 — FMEA

For each component in `05-architecture/components.csv`:

| column | what to write |
| --- | --- |
| component | the name |
| failure mode | how it fails — not why |
| effect | what the rest of the architecture does when it fails |
| detection | how anyone would know |
| mitigation | what makes the effect survivable |

Two rules:

- **An inability to describe the effect of a component's failure is itself the
  finding.** The book treats it as evidence of a poor architecture, and this is
  the final test of the work so far.
- Pay special attention to components that appeared *late* — the ones added for
  one residue. Those are where unreviewed complexity hides.

## Part 2 — ATAM

Now the trade-offs. For each contested decision:

- **Which residues are in tension?** Two residues can want opposite things.
- **Who disagrees, and about what?** Cost, ownership, timeline, control.
- **What is the sensitivity point?** The decision where a small change flips the
  outcome for one stakeholder.
- **What is the risk of deciding either way?**

This is where cost and probability are finally allowed back into the room. Not
before (residuality-theory §cost-and-over-engineering) —
letting them in earlier filters the simulation and hides the fault lines. Here
they are exactly the right tools.

## Part 3 — What you are recommending

Close with an explicit list:

- residues to implement now
- residues to leave designed but unbuilt (the architecture is primed for them,
  which is most of the value)
- residues to drop, and what is being accepted by dropping them

That third list is the honest one. Write it even when it is uncomfortable.

## Output

Markdown to the path in your prompt, structured as `## FMEA`, `## ATAM`,
`## Recommendation`. Use tables for the first two.

## Finishing

```bash
residual compile 07-review && residual gate 07-review
```

## Running this stage on its own

This stage is not self-sufficient: it reads artifacts earlier stages
produced.

- `05-architecture/components.csv` — from `05-architecture`
- `06-matrix/matrix.csv` — from `06-matrix`

Given those files in the run directory, nothing else about the pipeline has to
run, or even exist, for this stage to work.

```bash
python skills/residual-07-review/scripts/run.py plan      # expand this stage into work units
python skills/residual-07-review/scripts/run.py next      # claim one and print its prompt
python skills/residual-07-review/scripts/run.py compile   # merge the shards
python skills/residual-07-review/scripts/run.py gate      # the deterministic checks
python skills/residual-07-review/scripts/run.py report    # HTML, opens from file://
python skills/residual-07-review/scripts/run.py test      # this stage's own tests
```

Same kernel and same run directory as `residual <command> 07-review` — the stage
is implied rather than typed, so you cannot address another one by accident.

Everything this stage is made of lives in `skills/residual-07-review/`: this file,
`step.py` (what it declares, compiles and gates), its runner, and its
own tests.
