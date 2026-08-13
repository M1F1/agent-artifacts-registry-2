"""Step 01 — flow analysis: what this step declares, compiles and gates.

The first step has no inputs, which is what makes it the one you can always run
on its own: point it at a codebase and it produces the flows every later step
grounds itself in.
"""

from __future__ import annotations

from residual import fs, merge
from residual.config import Config
from residual.model import FLOW_COLUMNS, Flow, GateResult, Issue, StepSpec, flow_to_row
from residual.profiles import Profile
from residual.run import RunContext, compiled_path

SPEC = StepSpec(
    id="01-flows",
    title="Flow analysis",
    goal=(
        "List the actors and every movement of information between them. "
        "Not a process, not a use case -- those decompositions are the ones "
        "the theory rejects (residuality-theory §flow-analysis)."
    ),
    skill="skills/residual-01-flows/SKILL.md",
    inputs=(),
    output_template="01-flows/raw/{shard}.jsonl",
    compiled="01-flows/flows.csv",
    shard_by="single",
    record_type="flow",
    capabilities=("context.code", "context.docs", "context.lineage"),
)

OUTPUT_SCHEMA = """{
  "source": "actor the information leaves",
  "target": "actor it arrives at",
  "payload": "what information moves",
  "trigger": "what causes the movement -- a schedule, an event, a request",
  "notes": "anything worth stressing later (optional)",
  "tools_used": ["names of any context tools you actually called"]
}"""

GATE_RULES = (
    "- every flow names a real source, a real target and what actually moves\n"
    "- actors are people, systems and organisations, not layers or modules\n"
    "- a flow with no trigger is a guess; say what causes the movement"
)


def gate_rules(spec: StepSpec, config: Config, profile: Profile) -> str:
    return GATE_RULES


def compile_step(ctx: RunContext, spec: StepSpec) -> merge.CompileResult:
    """Number the flows in shard order, so ids never depend on write order."""
    flows = tuple(
        Flow(
            id=f"F{index:04d}",
            source=flow.source,
            target=flow.target,
            payload=flow.payload,
            trigger=flow.trigger,
            notes=flow.notes,
        )
        for index, flow in enumerate(merge.parse_flows(ctx, spec), start=1)
    )
    outputs = merge.write_table(
        compiled_path(ctx, spec), FLOW_COLUMNS, [flow_to_row(f) for f in flows]
    )
    return merge.CompileResult(spec.id, len(flows), merge.shard_count(ctx, spec), outputs)


def gate(
    ctx: RunContext, spec: StepSpec, config: Config, profile: Profile
) -> GateResult:
    """Flows are the vocabulary every later gate measures specificity against.

    So the check is coverage and completeness, not quality: a missing payload
    silently weakens the stressor gate three steps later.
    """
    rows = fs.read_csv(compiled_path(ctx, spec))
    issues: list[Issue] = []
    if not rows:
        issues.append(Issue(code="empty-flows", detail="no flows compiled"))

    for row in rows:
        empty = [f for f in ("source", "target", "payload") if not row.get(f, "").strip()]
        if empty:
            issues.append(
                Issue(
                    code="empty-field",
                    detail=f"missing {', '.join(empty)}",
                    where=row.get("id", "?"),
                )
            )

    actors = {r.get("source", "") for r in rows} | {r.get("target", "") for r in rows}
    return GateResult(
        step=spec.id,
        issues=tuple(issues),
        stats={"records": len(rows), "actors": len({a for a in actors if a})},
    )
