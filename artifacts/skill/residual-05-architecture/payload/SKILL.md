---
name: residual-05-architecture
description: Compress every residue into one coherent residual architecture and name its components. Use when running step 05 of a residual run.
---

# Step 05 — The residual architecture

## What you are producing

The component list of a single, coherent architecture that carries **all** the
residues at once. These names become the columns of the contagion matrix, so
they have to be stable nouns you can point at.

## This is the step residuality cannot teach you

The book says so directly: integrating residues into a coherent whole needs a
grounding in distributed systems and service orientation, and struggling here is
usually a gap in that knowledge rather than a misunderstanding of the method
(residuality-theory §contagion-analysis).

Build up from first principles. Do not reach for a reference architecture
because it is familiar — the pattern has to be justified by residues, not by
precedent.

## Procedure

1. **Read every residue.** Group the ones that demand the same capability.
2. **Name a component per capability**, not per residue. Twelve residues about
   contract drift, late data and backfills may all want the same thing.
3. **Decide what is shared and what is separate.** This is the real work: which
   residues can live behind one component, and which need their own because they
   fail differently.
4. **Record which residues drove each component.** A component no residue asked
   for is over-engineering, and the gate flags it.
5. **Do not silently drop a residue.** If you decide a residue's component is not
   worth having, that is a legitimate call — but the gate will report the drop,
   and it should be an argument you are prepared to have.

## On N, K and P

You are choosing N here — how many components exist. The matrix in step 06 will
tell you whether you chose well, so do not agonise now:

- too few, and every stressor hits everything;
- too many, and the system collapses under the weight of managing itself.

Criticality is the balance between those, and it is not the same as correctness
(residuality-theory §criticality). You are not trying to
build something that cannot be damaged. You are trying to build something that
can move between attractors cheaply.

P — biasing components toward uniform behaviour through consistent interfaces,
error handling and security — is worth noting in a component's purpose where it
applies. Raising P lowers the number of attractors, which is the cheapest lever
you have.

## Output

One JSON object per line:

```json
{
  "name": "TariffVersionStore",
  "kind": "one of the profile's component kinds",
  "purpose": "one line on what it is for",
  "residues": ["R0007", "R0012"]
}
```

Names are matched **exactly** in step 06. Pick them once and do not vary them.

## Finishing

```bash
residual compile 05-architecture && residual gate 05-architecture
```

## Running this stage on its own

This stage is not self-sufficient: it reads artifacts earlier stages
produced.

- `02-naive/architecture.md` — from `02-naive`
- `03-stressors/register.csv` — from `03-stressors`
- `04-residues/residues.csv` — from `04-residues`

Given those files in the run directory, nothing else about the pipeline has to
run, or even exist, for this stage to work.

```bash
python skills/residual-05-architecture/scripts/run.py plan      # expand this stage into work units
python skills/residual-05-architecture/scripts/run.py next      # claim one and print its prompt
python skills/residual-05-architecture/scripts/run.py compile   # merge the shards
python skills/residual-05-architecture/scripts/run.py gate      # the deterministic checks
python skills/residual-05-architecture/scripts/run.py report    # HTML, opens from file://
python skills/residual-05-architecture/scripts/run.py test      # this stage's own tests
```

Same kernel and same run directory as `residual <command> 05-architecture` — the stage
is implied rather than typed, so you cannot address another one by accident.

Everything this stage is made of lives in `skills/residual-05-architecture/`: this file,
`step.py` (what it declares, compiles and gates), its runner, and its
own tests.
