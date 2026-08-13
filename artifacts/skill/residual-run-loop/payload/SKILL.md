---
name: residual-run-loop
description: Drive a residuality step by restarting an agent process per work unit, giving every unit a genuinely cold context. Use when running a residual step from a shell with any headless agent command.
---

# Driving a residual step with a restart loop

## When to use this

Anywhere you have a shell and an agent that can be run headless: `claude -p`,
`codex exec`, anything that reads a prompt and writes files.

This is the **strongest** of the three modes, not the fallback. A fresh process
per unit means nothing leaks between generators except the files on disk, and
blind generators are exactly what random simulation depends on
(residuality-theory §random-simulation). Parallel
subagents come close; a single session does not come close at all.

## Procedure

```bash
skills/residual-run-loop/scripts/loop.sh 03-stressors "claude -p"
```

The script plans the step, then loops: render the next unit's prompt to a file,
start a fresh agent on it, repeat. It stops when `residual next` exits non-zero
— that is, when the queue is **drained**, which is convergence rather than a
budget running out. Then it compiles, reports and gates.

Two knobs, both environment variables:

- `PROMPT_FILE` — where the rendered prompt is written (default
  `.residuality/unit.md`, which is gitignored);
- `RESIDUAL` — how to invoke the CLI (default `python3 -m residual`).

If your agent takes a path rather than stdin, uncomment the variant at the
bottom of the script.

## Initialise the run honestly

```bash
python3 -m residual init "my-analysis" --mode loop --harness claude-code --model opus-5 --profile airflow-spark
```

`--mode loop` stamps `blind=true` on every record, and it is true: each unit ran
in a process that had never seen its siblings. That claim is what makes the
empirical test at step 09 mean anything, so do not stamp it on a run that was
really driven in one session.

## When a unit fails

The agent exiting non-zero leaves the unit **claimed**, not lost. It is
reclaimed automatically once its TTL expires (`claim_ttl_seconds`, default 30
minutes), and the next loop picks it up. To send it back immediately:

```bash
python3 -m residual fail 03-stressors--pestle-legal "wrote three generic rows"
```

## The other two modes

- `skills/residual-run-parallel/SKILL.md` — one subagent per unit, in Claude Code.
- `skills/residual-run-sequential/SKILL.md` — one session walking the queue, for
  Codex, Tabnine and anything else that can neither fork nor restart.

All three drive the same queue and produce the same artifacts. They differ only
in how cold each unit's context is, which the run records rather than polices.
