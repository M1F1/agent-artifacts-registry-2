---
name: residual-run-sequential
description: Drive a residuality step in a single session by walking the work queue, for harnesses without subagents or process restart. Use when running a residual step in Codex, Tabnine, or any single-context agent.
---

# Driving a residual step in one session

## When to use this

A harness that can read files and run shell commands, but cannot dispatch
subagents and cannot be restarted per unit. Codex and Tabnine typically land
here.

The artifacts are identical to the other two modes. The epistemics are not —
see the warning below, and initialise the run honestly.

## Procedure

Loop until the queue is drained:

```bash
python3 -m residual next --step 03-stressors
```

- It prints a self-contained prompt and exits **0**.
- Do the work described in that prompt, writing to the path it names.
- Run the `residual done <unit-id>` command it gives you.
- Run `residual next` again.
- When it exits **1** with `queue drained`, the step is finished.

Then:

```bash
python3 -m residual compile 03-stressors
python3 -m residual gate 03-stressors
python3 -m residual report 03-stressors
```

## The one thing that matters in this mode

**You will have every previous unit in your context.** That is the whole
problem. Blind generators are what makes random simulation work
(residuality-theory §random-simulation), and a single
session converges on itself: by the fourth lens you will be writing variations
of the first lens's answers without noticing.

Counter it deliberately:

- **Treat each unit as if you had never seen the others.** Read the new
  provocation, go back to the flows and the naïve architecture, and derive from
  those — not from what you already wrote.
- **Before writing a row, ask whether you are reaching for it because the lens
  suggests it or because you already used it.** If the latter, discard it.
- **Prefer a concrete thing you have not touched yet.** Work down the flow list
  rather than round the same two or three components.
- **If your harness can clear context between units, do it** — even losing the
  conversation is a net gain here. If it can restart the process entirely, stop
  using this mode and use `skills/residual-run-loop/scripts/loop.sh` instead, which is strictly
  better.

## Initialise the run honestly

```bash
python3 -m residual init "my-analysis" --mode in-session --harness tabnine --profile airflow-spark
```

`--mode in-session` stamps `blind=false` on every record produced. Nothing is
blocked by this. But when the empirical test later compares two architectures,
a register generated in one shared context is not comparable to one generated
blind, and the report will say so rather than quietly averaging them together.

Claiming `--mode loop` for a session run does not make the analysis better; it
only makes the number at the end unfalsifiable.
