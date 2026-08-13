"""The CLI a single skill exposes, so a stage can be run on its own.

``residual gate 06-matrix`` drives the whole pipeline from outside; this drives
one step from inside it:

    python skills/residual-06-matrix/scripts/run.py gate

Same kernel, same run directory, same exit codes -- the step is simply implied
rather than typed, and ``test`` runs that skill's own tests. It is what makes
"run the contagion analysis and stop" a thing you can actually do, and it is
how a skill stays independently exercisable even though its inputs come from
the steps before it.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

EXIT_OK = 0
EXIT_FAIL = 1


def build_parser(step_id: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"{step_id}",
        description=f"Run step {step_id} of a residuality analysis on its own.",
    )
    parser.add_argument("--root", help="path to the .residuality directory")
    parser.add_argument("--run", help="run slug (defaults to the most recent)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="what this step has produced so far")

    p = sub.add_parser("plan", help="expand this step into work units")
    p.add_argument("--replace", action="store_true", help="discard existing units")

    p = sub.add_parser("next", help="claim the next unit of this step and print its prompt")
    p.add_argument("--out", help="write the prompt here instead of stdout")

    p = sub.add_parser("done", help="mark a claimed unit finished")
    p.add_argument("unit")

    p = sub.add_parser("fail", help="requeue or park a unit")
    p.add_argument("unit")
    p.add_argument("reason")

    sub.add_parser("compile", help="merge this step's shards")
    sub.add_parser("gate", help="run this step's deterministic checks")
    sub.add_parser("report", help="render this step's report to HTML")
    sub.add_parser("spec", help="print what this step declares")
    sub.add_parser("test", help="run this skill's own tests")

    return parser


def main(step_file: str | Path, argv: Sequence[str] | None = None) -> int:
    """Entry point for a skill's ``scripts/run.py``.

    Takes the *skill's* file rather than a step id, so a copied skill directory
    needs no edit here to work. Finding the kernel already happened: that is the
    one thing the runner script has to do for itself, since it cannot import
    this module until it has.
    """
    from residual import cli, registry, testing

    skill_dir = Path(os.path.abspath(step_file)).parent.parent
    step_id = registry.step_id_at(skill_dir)

    args = build_parser(step_id).parse_args(argv)
    args.step = step_id

    if args.command == "test":
        return EXIT_OK if testing.run_skill(skill_dir) else EXIT_FAIL

    if args.command == "spec":
        spec = registry.spec(step_id)
        print(f"{spec.id}  {spec.title}")
        print(f"  shards by     {spec.shard_by}")
        print(f"  reads         {', '.join(spec.inputs) or '(nothing)'}")
        print(f"  writes        {spec.compiled}")
        print(f"  siblings      {spec.siblings}")
        if spec.forbidden_paths:
            print(f"  must not read {', '.join(spec.forbidden_paths)}")
        return EXIT_OK

    if args.command == "status":
        from residual import queue as queue_mod
        from residual import run as run_mod

        cfg, ctx = cli._context(args)
        spec = registry.spec(step_id)
        tally = queue_mod.counts(ctx, step_id)
        queued = ", ".join(f"{k}={v}" for k, v in tally.items() if v)
        compiled = run_mod.compiled_path(ctx, spec)
        print(f"run {ctx.slug}  mode={ctx.mode}  blind={'yes' if ctx.blind else 'no'}")
        print(f"  {spec.id:<14} {queued or 'no units'}")
        print(f"  {'compiled' if compiled.exists() else 'not compiled'}  {compiled}")
        return EXIT_OK

    handlers = {
        "plan": cli.cmd_plan,
        "next": cli.cmd_next,
        "done": cli.cmd_done,
        "fail": cli.cmd_fail,
        "compile": cli.cmd_compile,
        "gate": cli.cmd_gate,
        "report": cli.cmd_report,
    }
    try:
        return int(handlers[args.command](args))
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"{step_id}: {exc}", file=sys.stderr)
        return EXIT_FAIL
