---
name: residual-run-parallel
description: Drive a residuality step with parallel subagents, one per work unit. Use in Claude Code when running a residual step and subagents are available.
---

# Driving a residual step with parallel subagents

## When to use this

Claude Code, or any harness that can dispatch isolated subagents. If subagents
are unavailable, use `skills/residual-run-sequential/SKILL.md` instead — same queue, same
artifacts, weaker blindness.

## Procedure

1. **Expand the step into work units.**

   ```bash
   python3 -m residual plan 03-stressors
   ```

   This prints the unit ids. There is one per lens.

2. **Render each unit's prompt without claiming it**, so you can hand it to a
   subagent:

   ```bash
   python3 -m residual prompt 03-stressors--upstream-contract
   ```

3. **Dispatch one subagent per unit.** Each subagent gets:
   - the rendered prompt as its entire task, and
   - permission to run `residual done <unit-id>` when finished.

   Alternatively, have each subagent call `residual next --step <step>` itself,
   which claims a unit atomically. Two subagents cannot claim the same unit —
   the claim is an `os.replace`, so exactly one rename wins.

4. **Do not summarise the units to each other.** Do not run a "review and merge"
   pass over the stressors before compiling. Consensus between generators is the
   failure mode random simulation exists to avoid
   (residuality-theory §random-simulation); the dedupe
   happens in the gate, after the fact, on evidence.

5. **Compile, gate, report.**

   ```bash
   python3 -m residual compile 03-stressors
   python3 -m residual gate 03-stressors
   python3 -m residual report 03-stressors
   ```

6. **If the gate fails**, requeue the offending units rather than editing the
   register by hand:

   ```bash
   python3 -m residual fail 03-stressors--pestle-legal "3 generic rows, 1 with a probability field"
   ```

   A requeued unit goes back to `pending/` with its attempt count raised, and a
   fresh subagent picks it up.

## What you must not do as the orchestrator

- **Do not read the shard outputs while units are still running.** Nothing
  stops you technically. But if you then brief a later subagent, you have
  transmitted the earlier ones' answers, and the blindness recorded in the
  provenance becomes a lie.
- **Do not filter stressors for plausibility.** No probability, no cost, no
  "that won't happen". Those filters are what the method removes on purpose
  (residuality-theory §stressors).
- **Do not add lenses on the fly to fill a gap.** Add them to a profile so the
  next run is comparable to this one.

## Recording the mode

The run was initialised with a mode, and every record carries it:

```bash
python3 -m residual init "my-analysis" --mode parallel --harness claude-code --model opus-5 --profile airflow-spark
```

Mode matters because the empirical test later compares architectures, and a
register generated in a shared context is not comparable to one generated
blind. The kernel records it rather than policing it.
