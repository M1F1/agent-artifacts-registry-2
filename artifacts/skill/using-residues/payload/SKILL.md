---
name: using-residues
description: The residuality kernel and the map of the residual-* skills — which stage to run, what it needs on disk first, how to stop between stages, and how to invoke the CLI every stage shares. Use when starting, resuming or orchestrating a residuality analysis, or when a residual-* skill needs the kernel.
---

# Using the residues skills

This skill is two things: the **map** of the pipeline, and the **kernel** every
other `residual-*` skill runs on. Install it first; the stage skills expect to
find it beside them.

## The kernel

```
using-residues/
  SKILL.md              this file
  config.example.toml   the per-project config, copied into .residuality/
  kernel/
    bin/residual        the CLI, with nothing installed
    residual/           the package: queue, run dirs, gates, prompts, reports
    tests/              the kernel's own tests
```

Python 3.11+ and **no dependencies** — not at runtime, not for tests. That is a
constraint rather than a boast: a skill you fetch has to run on whatever Python
is already on the machine.

```bash
# from wherever this skill was installed
skills/using-residues/kernel/bin/residual where     # which kernel, which skills
skills/using-residues/kernel/bin/residual steps     # the pipeline as installed
skills/using-residues/kernel/bin/residual-test      # kernel + every skill's tests
```

Prefer `residual` on your PATH? `pip install -e skills/using-residues/kernel`.
Same code, same zero dependencies, and the stage runners find it either way.

### How the stages find it

Every stage skill resolves the kernel at startup, in this order:

1. `RESIDUAL_KERNEL`, if you set it;
2. `../using-residues/kernel` — the sibling layout, which holds both in the
   framework repository and in an installed skills directory;
3. an installed `residual` package on `sys.path`.

So `.claude/skills/residual-06-matrix/scripts/run.py` works because
`.claude/skills/using-residues/kernel/` is right there. Install a stage skill
without this one and it says so, naming the directories it looked in.

`RESIDUAL_SKILLS` overrides where the kernel looks for stages, which is how you
run a modified or extended pipeline without touching the kernel.

## The shape of a stage

Nine stages, each a skill that carries its own code and its own tests:

```
skills/residual-06-matrix/
  SKILL.md          the procedure — what a contagion row is, what makes one good
  step.py           what the stage declares, compiles and gates
  matrix.py         the arithmetic, used by this stage and nothing else
  report.py         the heatmap and the refactoring triggers
  scripts/run.py    plan · next · compile · gate · report · test, this stage only
  tests/            this stage's tests
```

Nothing in a stage's directory knows about any other stage. What they share
lives in the kernel, under one rule: **code used by exactly one stage lives in
that stage; code used by two or more lives in the kernel.**

## The pipeline

| Stage | Reads | Produces |
| --- | --- | --- |
| `residual-01-flows` | nothing | actors and the information moving between them |
| `residual-02-naive` | flows | the deliberately unimaginative control architecture |
| `residual-03-stressors` | flows, naïve | the stressor register |
| `residual-04-residues` | naïve, register | concrete changes, and the **looping rate** |
| `residual-05-architecture` | naïve, register, residues | the residual architecture's components |
| `residual-06-matrix` | register, components | the contagion matrix and its refactoring triggers |
| `residual-07-review` | components, matrix | FMEA and ATAM over what the earlier stages added |
| `residual-08-holdout` | flows **only** | fresh stressors that never saw the residues |
| `residual-09-ri` | naïve, components, holdout | blind survival judgments → `Ri = (Y − X) / S` |

Only the stages you installed appear in `residual steps`. A partial install is a
shorter pipeline, not a broken one.

## Starting a run

```bash
mkdir -p .residuality
cp skills/using-residues/config.example.toml .residuality/config.toml
skills/using-residues/kernel/bin/residual init "my-analysis" --mode loop --profile airflow-spark
```

`config.toml` is where MCP tools bind to the capabilities stages ask for, where
gate thresholds are tuned, and where a stage's granularity is widened or
narrowed. Workplace-private profiles go in `.residuality/profiles/`, never in a
shared catalog.

## Running one stage, then stopping

Stages are meant to be run one at a time, with a human reading the report in
between. That is not a limitation of the tooling: the matrices and lists are
valuable because of the arguments they start (residuality-theory §the-artifacts).

```bash
python skills/residual-03-stressors/scripts/run.py plan
# work the units — see the run-mode skills below
python skills/residual-03-stressors/scripts/run.py compile
python skills/residual-03-stressors/scripts/run.py gate
python skills/residual-03-stressors/scripts/run.py report
```

Stop there. Read the report. Argue with it. Then start the next stage.

A stage needs its inputs to exist, nothing more. Hand `residual-03-stressors` a
flows file and a naïve architecture written by hand and it runs, never asking
where they came from. Resuming needs no state in your context: the queue *is*
the progress record, and `residual status` says what is done.

## Which run-mode skill

The stage says *what* to do; these say *how* to drive its units:

- `residual-run-parallel` — one subagent per unit (Claude Code).
- `residual-run-loop` — one restarted agent process per unit (any shell). The
  strongest: every unit gets a genuinely cold context.
- `residual-run-sequential` — one agent walking the queue in one conversation,
  for Codex, Tabnine and anything else that can neither fork nor restart. The
  weakest, and the run records it as not blind rather than pretending.

They are execution models, not vendors. A harness needs its own skill only if
its mechanics differ from all three.

## Two isolation rules that are opposites

Get these the wrong way round and the analysis is quietly ruined:

- `residual-03-stressors` and `residual-08-holdout` **forbid** reading sibling
  shards. Generators that see each other converge (residuality-theory §random-simulation).
- `residual-04-residues` **requires** it. Noticing that an earlier residue
  already covers this stressor is the looping measurement itself
  (residuality-theory §looping-and-convergence).

Stricter than both: `residual-09-ri` must not open any file in the run
directory. Both architectures are inlined in its prompt as A and B, and a file
path would tell the judge which is which.

## Adding a stage

Create a directory beside this one with a `SKILL.md` and a `step.py` exporting
`SPEC`, `compile_step` and `gate`. The kernel discovers it — there is no list to
edit. Optional hooks: `OUTPUT_SCHEMA`, `gate_rules`, `prompt_context`, `report`.

## What never changes, whichever stage you are in

- **No probability, no impact, no cost, no priority** during simulation. They
  are rejected by the schema, not merely discouraged (residuality-theory §stressors).
  Stage 07 is the one place cost is allowed, and by then the simulation is over.
- **Nothing generic.** A row that would read identically at another company is
  filler, and the gate measures it.
- **State lives in files, never in your context.**

## Where the reasoning lives

Citations of the form `residuality-theory §stressors` point at sections of the
**`residuality-theory` guideline**, a condensed reference that ships alongside
these skills: what a stressor is and is not, why probability is banned, what
looping measures, how to read the contagion matrix, what `Ri` does and does not
say. Install it with the bundle if you want the reasoning behind a rule; the
skills are executable without it.

The theory is Barry M O'Reilly's, from *Residues: Time, Change, and Uncertainty
in Software Architecture*. The guideline is a summary written for this
framework, not a substitute for the book — read it for the derivations, the
worked examples and the argument.
