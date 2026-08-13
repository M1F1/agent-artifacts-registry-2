---
name: residuality-theory
description: A condensed working reference for Residuality Theory — stressors, attractors, residues, criticality, the contagion matrix and the residual index — written for the agents and humans driving the residual-* skills. Use when a skill cites a concept and you want the reasoning behind it.
---

# Residuality theory — a working reference

## What this is, and what it is not

This is a **condensed reference written for this framework**: the concepts the
`residual-*` skills depend on, in the order the pipeline meets them, with the
reasoning that makes each rule non-negotiable. It is deliberately short, and it
is **not** the book.

The theory is Barry M O'Reilly's, set out in *Residues: Time, Change, and
Uncertainty in Software Architecture*, and developed in his papers on residuality
and hyperliminality. Nothing here substitutes for reading it: the book carries
the derivation, the worked examples, the empirical results and the argument with
the rest of the discipline. What follows is a practitioner's summary, in this
framework's words, so that a cold agent can act correctly without the book in
its context.

Skills cite it as `residuality-theory §section`.

---

## §the-problem

Architecture is usually taught as decomposition: take the requirements, break
the system into parts, assign responsibilities. This works when the context is
stable and known. It fails in the ordinary case, where the requirements describe
one moment in the life of a business that will keep moving after you ship.

The failures that hurt are rarely the ones in the requirements. They come from
the **context** — a regulator, a competitor, a merger, a habit users pick up, a
supplier that goes away. None of those are bugs. Each of them changes what the
system was supposed to be, and an architecture that can only be correct against
the original statement has no answer.

Residuality's move is to stop treating the specification as the object of design
and start treating the **environment around it** as the thing to design against.

## §criticality

A system can be **correct** and still be worthless the moment its context moves.
Correctness is a relationship between an artifact and a specification.
Criticality is a relationship between an artifact and a *changing world*: how
close the design sits to the point where it survives shocks nobody wrote down.

The two are not opposites, and criticality is not a score. It is a direction you
can move in, and the only honest claim you can make about a round of this work
is whether it moved you that way. That is what §empirical-test measures.

Practically: a critical architecture is one where the surprises the world
produces keep landing on structures that already exist, rather than on
assumptions that have to be torn out.

## §random-simulation

You cannot enumerate the future, so residuality does not try. It **samples** it:
generate many independent, specific, plausible stories about how the context
changes, and see what they demand.

The word that matters is *independent*. Two conditions ruin the sampling:

- **A group in one room.** People converge. The second contribution is shaped by
  the first, and a workshop's output looks like consensus rather than coverage.
- **One agent in one context.** By the fourth lens it is producing variations of
  what it already wrote, and it does not notice, because everything it wrote
  looks reasonable to it.

This is why the pipeline's generation stages run **blind**: one unit per lens,
each in a context that never saw its siblings. It is also why blindness is
recorded on every record rather than assumed — a run that could not be blind is
still useful, but its numbers are not comparable to one that was.

Deduplication happens *after the fact*, mechanically, on evidence. Filtering
during generation is exactly the thing that destroys the sample.

## §naive-architecture

Before stressing anything you write the architecture that solves the problem
**exactly as stated** — no more. The smallest, most obvious, least imaginative
arrangement that satisfies the requirements as written.

It is not a strawman and it is not a draft. It is the **control arm**: the thing
the residual architecture will be compared against when the empirical test asks
whether all this work bought anything. Improving it — anticipating stress,
adding the component you already know you will need — contaminates the
comparison and makes the final number meaningless.

Write down the obvious assumptions too, the ones that feel too dull to state.
"A customer is a person." "A reading arrives once." "The price is a number."
Those are where the interesting stress lands (§edge-cases-and-abstractions).

## §stressors

**A stressor is any fact about the context that is currently outside your
understanding of the system.**

It is not a risk, not a requirement, not an edge case, not a failure mode. It
does not need to be likely, agreed, or costed. It needs exactly one thing: a
coherent story about how this business ends up somewhere different.

What a stressor is *not*, and why the distinction is load-bearing:

| Not this | Because |
| --- | --- |
| a risk | risks carry probability and get triaged; stressors are not scored |
| a requirement | requirements describe the known; stressors describe the unknown |
| an edge case | edge cases live inside the current abstraction (§edge-cases-and-abstractions) |
| a failure mode | failure modes are internal; stressors come from outside the machine |

### No probability, no impact, no cost, no priority

This is the rule people push back on hardest, and it is the one that does the
most work. The moment you score a stressor, you filter the list — and you filter
out precisely the improbable-sounding ones that carry the information. Cost
filters it the same way probability does, just later in the sentence.

Scoring has a place. It is called §fmea-atam, and it happens after the
simulation is over, when you are deciding what to *build*.

### Nothing generic

"The database goes down." "Traffic spikes." "A dependency fails." These are true
of every system ever built, which is another way of saying they tell you nothing
about yours. A stressor names the real table, the real team, the real product,
the real regulator. If it would read identically in another company's analysis,
it is filler.

### Quantity is not padding

A serious analysis produces hundreds of rows, and the last ones are usually
better than the first. The reason is §attractors: many different stressors lead
to the same settled state, so each one you write is a lottery ticket on
discovering a structure that covers dozens you never thought of.

## §attractors

Do not stop at the moment of impact. Ask "and then what?" three or four times,
until the business has **settled** somewhere. That settled state — not the
incident, the new normal — is the attractor, and it is where all the value is.

The incident is transient and specific. The attractor is durable and shared: a
regulator's ruling, a competitor's pricing move and an angry customer segment
can all push a business into the same new operating reality. Design for the
attractor and you have covered every path into it, including the ones you never
imagined.

An attractor is a *business* state, described in the business's language. "The
finance team rebuilds the month by hand every night" is an attractor. "The
service is degraded" is not.

## §residues

A **residue** is what is left in the architecture after a stressor has been
thought through: the concrete change that lets the system survive the attractor.

It is specific. "Add validation" and "improve monitoring" are not residues; "the
price is pinned at order time in a versioned store, so a retroactive tariff edit
cannot reprice yesterday" is. The name comes from what remains once the shock has
passed through: the structures that outlive the event.

Not every stressor produces a technical residue. Plenty are absorbed by a
business reaction — a policy, a price change, a new team, a phone call. Recording
that honestly is part of the method, not a gap in it. Not everything is solved
with software.

## §looping-and-convergence

As the register grows, something specific starts happening: new stressors turn
out to be **already survived** by residues designed earlier.

This is the signal the whole method exists to produce. It means the architecture
has begun absorbing the shape of its environment rather than a list of individual
shocks. The rate of it — how often a new stressor needs nothing new — is the
practical indicator that you are approaching §criticality.

So looping is **counted, never penalised**. A rate near zero means there is more
stressing to do. A rate that climbs and then plateaus is the signal to stop:
further rounds will buy less and less. This is also why the work terminates on
convergence rather than on a budget or a schedule.

For this to be measurable, residue design is the one stage that **must** see its
siblings. Blind generation is right for stressors (§random-simulation) and wrong
here: noticing that an earlier residue already covers this attractor *is* the
measurement.

## §edge-cases-and-abstractions

The richest source of stressors is your own vocabulary. Every abstraction in the
naive architecture is a bet that some part of the world will keep behaving like
one thing.

When a noun stops fitting, the instinct is to extend it: add an optional field,
a flag, a subtype. Residuality says the opposite. **The noun was two things all
along**, and the honest move is to break it.

- "A customer" was a person, until a housing association arrives with four
  thousand supply points.
- "A reading" was a number, until the meter sends corrections for last month.
- "A price" was a value, until it becomes a value *with a time it was true*.

An edge case is a question asked from inside the abstraction. A stressor is
what happens when the abstraction itself stops being true.

## §technical-skew

Architects with deep technical backgrounds produce technical stressors: servers,
timeouts, deploys, certificates, caches. It feels like work, and it is the most
common way for an analysis to fail quietly.

A list dominated by the machine room means the simulation never left the
building. The stress that reshapes architectures comes from markets, regulation,
money, and people. The technical layer is downstream of all of them.

This framework enforces a quota rather than a ban — some infrastructure stress is
real — and reports the share so a skewed run is visible instead of flattering.

## §the-artifacts

The method's output is deliberately mundane: **lists and matrices**. A register
of stressors with their attractors and reactions; a list of residues; a matrix
of stressors against components.

Their value is not that they are complete or authoritative. It is that they are
*arguable*. A spreadsheet in front of four people who own different parts of the
system produces the conversation the architecture actually needed. That is the
deliverable — the conversation, provoked by something concrete enough to
disagree with.

## §flow-analysis

Before the naive architecture, describe the system as **actors and the movement
of information between them**.

Not processes. Not use cases. Those decompositions bake in the sequence the
business happens to follow today, and the sequence is one of the first things
the context changes. Flows survive that: who tells whom what, and what triggers
it, remains legible when the process around it is rearranged.

Flows also become the **vocabulary** the rest of the analysis is grounded in.
That is what makes "nothing generic" (§stressors) mechanically checkable: a
stressor is specific if it names something this analysis actually discovered.

## §contagion-analysis

Once residues are compressed into a coherent architecture with named components,
build the incidence matrix: **stressors as rows, components as columns, 1 where
the stressor reaches the component**.

The arithmetic is trivial and should never be done by a model — a miscounted
column produces a plausible-looking refactoring plan built on a wrong number.
Read it for the following signals.

1. **Hot rows** — a stressor touching many components has a wide blast radius.
   This is where coupling that no diagram shows actually lives.
2. **Hot columns** — a component reached by many stressors is either doing too
   many jobs and wants splitting, or is genuinely central and wants redundancy.
   The matrix cannot tell you which; that is the argument to have.
3. **Two or more 1s in a row** — the components in that row are coupled *through
   the environment*. If they have no functional dependency on each other, you
   have found hyperliminal coupling: invisible in the code, real in the world.
4. **Identical column signatures** — two components that respond to stress
   identically live and die together. Merging them lowers the number of moving
   parts and the operating cost that comes with it.
5. **Cluster the attractors** — look at which components are damaged together
   under one attractor rather than one stressor at a time.
6. **Density** — the ratio of 1s to cells says how tangled the design is
   relative to its size (§nk-and-tuning).
7. **Empty columns** — a component nothing reaches is far more likely to be
   under-stressed than invulnerable. Treat a zero column as a gap in the
   analysis, not a clean bill of health.

**Hyperliminal** is the term for this whole layer: the couplings that exist
across the boundary between the system and its context, which functional
decomposition cannot see because they are not functional relationships at all.

## §nk-and-tuning

The matrix is a network. Counting nodes (N) and links (K) borrows from Kauffman's
work on fitness landscapes: raising K makes a system's behaviour increasingly
rugged and interdependent, so a change anywhere pulls on everything.

The practical reading: for a given N, the more of the matrix is filled, the more
tightly this design is coupled to its environment, and the more each residue
costs you elsewhere. It is a tuning instrument for the conversation, not a target
to optimise. Nobody should be gaming K.

## §fmea-atam

The earlier stages **add** components, and every added component fails, costs
money and belongs to somebody. Reviewing what your own analysis introduced is
part of the method:

- **FMEA** — for each new component, how does it fail, how would you notice, what
  happens downstream. Technical, concrete, per component.
- **ATAM** — the trade-offs between residues: cost, ownership, politics, the
  quality attributes they pull against each other.

This is the stage where cost and priority are not only allowed but required.
They were banned during simulation so they could not filter it (§stressors);
here the simulation is over and you are deciding what to build.

## §cost-and-over-engineering

The standard objection is that this produces over-engineering. Two answers.

First, a residue is a **design decision, not a work item**. Knowing where the
system will have to split does not oblige you to split it today; it changes where
you draw the line so that the split stays cheap. Much of the value is in things
you deliberately do *not* build yet.

Second, the comparison is not against a system with no residues — it is against
the cost of discovering the same thing in production, in a hurry, with customers
watching. That is the expensive path, and it is the default one.

An architecture that survived stress it was never designed for did not get lucky.
It got a structure that happened to match the shape of its environment, and that
match is what the work is for.

## §empirical-test

This is the part that makes residuality falsifiable, and it is unusual in
software architecture for that reason.

Take a set of **holdout stressors** — generated from the flows alone, by someone
or something that has never seen the residues. Judge each architecture, the naive
one and the residual one, on whether it survives each holdout stressor. Then:

```
Ri = (Y − X) / S
```

where `S` is the number of unseen stressors judged for both, `X` is how many the
naive architecture survives, and `Y` how many the residual one survives.

- **Ri > 0** — this round of work moved the architecture toward criticality.
- **Ri = 0** — it bought nothing measurable; further rounds have diminishing
  returns.
- **Ri < 0** — either the added components brought their own fragility, or the
  judging is not reliable.

Two conditions decide whether the number means anything at all:

- **The holdout must never have seen the residues.** A contaminated test set
  inflates `Y` without the architecture having earned it. A human doing this by
  hand cannot unsee a week of design work; independently generated units can.
- **The judge must not know which architecture is which.** Present them as A and
  B, in one voice, with the assignment hidden — and require every claimed
  survival to name the mechanism that absorbs the stressor. An unfalsifiable
  "it would probably cope" is the characteristic failure of model judging.

Ri is a **direction, not a grade**. It is comparable only within one judge and
one execution mode, and it says nothing about whether the architecture is good —
only whether this round improved its odds against stress nobody predicted.

## §safety-nets

No single stage in this method is trustworthy on its own. Each is a net under the
previous one, and the design assumes each will leak:

- flows ground everything in this system's real vocabulary;
- blind generation keeps the sample from collapsing into consensus;
- the residue stage catches stressors that need nothing new;
- the matrix catches components nothing reaches and couplings nobody drew;
- FMEA and ATAM catch what the analysis itself introduced;
- the empirical test catches the possibility that none of it helped.

Skipping one does not merely lose its output. It removes a check on everything
upstream of it, and the failures that result are the quiet kind: an analysis that
looks complete and is confidently wrong.

---

*Concepts: Barry M O'Reilly, "Residues: Time, Change, and Uncertainty in Software
Architecture". This summary is written for the residual-\* skills and is no
substitute for the original.*
