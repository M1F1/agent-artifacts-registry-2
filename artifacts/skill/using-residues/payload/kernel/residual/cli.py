"""The command line: the one interface every harness shares.

Claude Code drives it from parallel subagents, a shell loop drives it by
restarting an agent process per unit, and a single agent in a harness with
neither can walk the same queue in one session. None of them need to know which
of the three is happening.

Exit codes carry meaning, because the restart loop depends on them:
``next`` exits 1 when the queue is drained, which is how the loop terminates on
convergence rather than on a token budget, and ``gate`` exits 1 when a step has
not earned the right to be built on.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import config as config_mod
from . import fs, merge
from . import profiles as profiles_mod
from . import prompt as prompt_mod
from . import queue as queue_mod
from . import paths, registry
from . import run as run_mod
from . import steps as steps_mod
from . import testing, validate
from .model import GateResult, StepSpec
from .render import report as report_mod

EXIT_OK = 0
EXIT_FAIL = 1


# --------------------------------------------------------------------------
# resolution helpers
# --------------------------------------------------------------------------


def _config(args: argparse.Namespace) -> config_mod.Config:
    root = Path(args.root).resolve() if args.root else config_mod.find_root()
    return config_mod.load(root)


def _context(args: argparse.Namespace) -> tuple[config_mod.Config, run_mod.RunContext]:
    cfg = _config(args)
    slug = args.run or run_mod.latest_slug(cfg.root)
    if not slug:
        raise SystemExit(
            f"no runs under {cfg.root / 'runs'} -- start one with "
            "`residual init <name>`"
        )
    return cfg, run_mod.load(cfg.root, slug)


def _profile(
    cfg: config_mod.Config, ctx: run_mod.RunContext
) -> profiles_mod.Profile:
    names = ctx.profiles or cfg.profiles
    if not names:
        return profiles_mod.Profile()
    return profiles_mod.load(names, cfg.profile_search_paths)


def _spec(step_id: str) -> StepSpec:
    try:
        return steps_mod.by_id(step_id)
    except KeyError as exc:
        raise SystemExit(str(exc)) from exc


def _print_gate(gate: GateResult) -> None:
    for issue in gate.errors + gate.warnings:
        where = f" [{issue.where}]" if issue.where else ""
        print(f"  {issue.severity:<7} {issue.code}{where}: {issue.detail}")
    summary = ", ".join(
        f"{k}={v}"
        for k, v in sorted(gate.stats.items())
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    )
    print(f"  {'PASS' if gate.ok else 'FAIL'}  {summary}")


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    cfg = _config(args)
    slug = run_mod.slugify(args.name)
    ctx = run_mod.RunContext(
        root=cfg.root,
        slug=slug,
        mode=args.mode,
        harness=args.harness or "",
        model=args.model or "",
        profiles=tuple(args.profile) if args.profile else tuple(cfg.profiles),
    )
    run_mod.create(ctx)
    print(f"run {slug} at {ctx.dir}")
    print(f"  mode={ctx.mode} blind={'yes' if ctx.blind else 'no'}")
    if not ctx.blind:
        print(
            "  note: in-session mode shares one context across units, so "
            "generators can see each other. Recorded on every record."
        )
    if ctx.profiles:
        print(f"  profiles={', '.join(ctx.profiles)}")
    return EXIT_OK


def cmd_steps(args: argparse.Namespace) -> int:
    """The pipeline as it is actually installed: one line per step skill."""
    for spec in registry.specs():
        skill = registry.skill_dir(spec.id).name
        print(f"{spec.id:<14} {spec.title:<24} shard_by={spec.shard_by:<10} skills/{skill}")
    return EXIT_OK


def cmd_test(args: argparse.Namespace) -> int:
    """Kernel tests plus every skill's own, or just the ones you name."""
    if args.step:
        dirs = tuple(registry.skill_dir(step) / "tests" for step in args.step)
    else:
        dirs = testing.all_test_dirs()
    for directory in dirs:
        print(f"  {directory}")
    sys.stdout.flush()
    return EXIT_OK if testing.run(dirs, verbosity=2 if args.verbose else 1) else EXIT_FAIL


def cmd_where(args: argparse.Namespace) -> int:
    """Which kernel and which skills this command is actually using.

    The kernel ships inside a skill and is found by layout, so when something
    is mysteriously the wrong version, this is the first thing to look at.
    """
    for label, value in paths.describe():
        print(f"  {label:<14} {value}")
    print()
    for spec in registry.specs():
        print(f"  {spec.id:<14} {registry.skill_dir(spec.id)}")
    return EXIT_OK


def cmd_status(args: argparse.Namespace) -> int:
    cfg, ctx = _context(args)
    print(f"run {ctx.slug}  mode={ctx.mode}  blind={'yes' if ctx.blind else 'no'}")
    for spec in steps_mod.STEPS:
        tally = queue_mod.counts(ctx, spec.id)
        compiled = run_mod.compiled_path(ctx, spec)
        mark = "compiled" if compiled.exists() else "-"
        queued = ", ".join(f"{k}={v}" for k, v in tally.items() if v)
        print(f"  {spec.id:<14} {queued or 'no units':<44} {mark}")
    return EXIT_OK


def cmd_plan(args: argparse.Namespace) -> int:
    cfg, ctx = _context(args)
    spec = _spec(args.step)
    profile = _profile(cfg, ctx)
    units = steps_mod.expand(spec, profile, cfg, run_dir=ctx.dir)
    written = queue_mod.plan(ctx, units, replace=args.replace)
    print(f"{spec.id}: {len(written)} unit(s) queued of {len(units)} total")
    for unit in written:
        print(f"  {unit.id}")
    return EXIT_OK


def cmd_next(args: argparse.Namespace) -> int:
    cfg, ctx = _context(args)
    ttl = int(config_mod.gate(cfg, "claim_ttl_seconds"))
    unit = queue_mod.claim(ctx, step=args.step or "", ttl_seconds=ttl)
    if unit is None:
        print("queue drained", file=sys.stderr)
        return EXIT_FAIL

    spec = _spec(unit.step)
    profile = _profile(cfg, ctx)
    text = prompt_mod.render(unit, spec, ctx, cfg, profile)

    if args.out:
        fs.write_text(Path(args.out), text)
        print(unit.id)
    else:
        print(text)
    return EXIT_OK


def cmd_prompt(args: argparse.Namespace) -> int:
    cfg, ctx = _context(args)
    for state in queue_mod.STATES:
        path = queue_mod.unit_path(ctx, state, args.unit)
        if path.exists():
            from .model import unit_from_mapping

            unit = unit_from_mapping(fs.read_json(path))
            spec = _spec(unit.step)
            print(prompt_mod.render(unit, spec, ctx, cfg, _profile(cfg, ctx)))
            return EXIT_OK
    raise SystemExit(f"unit {args.unit!r} not found in this run's queue")


def cmd_done(args: argparse.Namespace) -> int:
    cfg, ctx = _context(args)
    unit = queue_mod.complete(ctx, args.unit)
    remaining = queue_mod.counts(ctx, unit.step)
    print(f"done {unit.id}; {remaining['pending']} pending in {unit.step}")
    return EXIT_OK


def cmd_fail(args: argparse.Namespace) -> int:
    cfg, ctx = _context(args)
    limit = int(config_mod.gate(cfg, "max_attempts"))
    unit, state = queue_mod.fail(ctx, args.unit, args.reason, max_attempts=limit)
    print(f"{unit.id} -> {state} (attempt {unit.attempts}/{limit}): {args.reason}")
    return EXIT_OK


def cmd_compile(args: argparse.Namespace) -> int:
    cfg, ctx = _context(args)
    spec = _spec(args.step)
    result = merge.run(ctx, spec)
    print(f"{spec.id}: {result.records} record(s) from {result.shards} shard(s)")
    for path in result.outputs:
        print(f"  {path}")
    return EXIT_OK


def cmd_gate(args: argparse.Namespace) -> int:
    cfg, ctx = _context(args)
    spec = _spec(args.step)
    gate = validate.run(ctx, spec, cfg, _profile(cfg, ctx))
    print(f"{spec.id}:")
    _print_gate(gate)
    return EXIT_OK if gate.ok else EXIT_FAIL


def cmd_report(args: argparse.Namespace) -> int:
    cfg, ctx = _context(args)
    spec = _spec(args.step)
    profile = _profile(cfg, ctx)
    gate = validate.run(ctx, spec, cfg, profile)
    html = report_mod.build(ctx, spec, gate, profile)

    target = run_mod.report_path(ctx, spec)
    fs.write_text(target, html)
    print(target)
    return EXIT_OK


def cmd_ri(args: argparse.Namespace) -> int:
    """Print the empirical test result and what it does and does not mean.

    The arithmetic and its caveats belong to the ``09-ri`` skill; this only
    prints what that skill says.
    """
    cfg, ctx = _context(args)
    lines, ok = registry.call("09-ri", "summary", ctx)
    for line in lines:
        print(line)
    return EXIT_OK if ok else EXIT_FAIL


def cmd_profile(args: argparse.Namespace) -> int:
    cfg, ctx = _context(args)
    profile = _profile(cfg, ctx)
    lenses = profiles_mod.all_lenses(profile)
    print(f"profiles: {', '.join(profile.names) or '(none)'}")
    print(f"components: {', '.join(profile.component_kinds) or '(none)'}")
    print(f"lenses ({len(lenses)}):")
    for lens in lenses:
        print(f"  {lens.id:<28} kind={lens.kind}")
    return EXIT_OK


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="residual",
        description="Residuality analysis: stressor-driven architecture, one work unit at a time.",
    )
    parser.add_argument("--root", help="path to the .residuality directory")
    parser.add_argument("--run", help="run slug (defaults to the most recent)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create a run")
    p.add_argument("name")
    p.add_argument(
        "--mode",
        default="in-session",
        choices=("parallel", "loop", "in-session"),
        help="parallel and loop give each unit a cold context; in-session does not",
    )
    p.add_argument("--harness", help="e.g. claude-code, codex, tabnine")
    p.add_argument("--model")
    p.add_argument("--profile", action="append", help="repeatable; later profiles win")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("steps", help="list the pipeline steps")
    p.set_defaults(func=cmd_steps)

    p = sub.add_parser("status", help="queue and artifact state for a run")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("plan", help="expand a step into work units")
    p.add_argument("step")
    p.add_argument("--replace", action="store_true", help="discard existing units")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("next", help="claim the next unit and print its prompt")
    p.add_argument("--step", help="restrict to one step")
    p.add_argument("--out", help="write the prompt here instead of stdout")
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("prompt", help="re-render a unit's prompt without claiming")
    p.add_argument("unit")
    p.set_defaults(func=cmd_prompt)

    p = sub.add_parser("done", help="mark a claimed unit finished")
    p.add_argument("unit")
    p.set_defaults(func=cmd_done)

    p = sub.add_parser("fail", help="requeue or park a unit")
    p.add_argument("unit")
    p.add_argument("reason")
    p.set_defaults(func=cmd_fail)

    p = sub.add_parser("compile", help="merge shards into the register")
    p.add_argument("step")
    p.set_defaults(func=cmd_compile)

    p = sub.add_parser("gate", help="run a step's deterministic checks")
    p.add_argument("step")
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("report", help="render the step report to HTML")
    p.add_argument("step")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("ri", help="print the residual index and its caveats")
    p.set_defaults(func=cmd_ri)

    p = sub.add_parser("profile", help="show the resolved profile and its lenses")
    p.set_defaults(func=cmd_profile)

    p = sub.add_parser("where", help="which kernel and skills this command is using")
    p.set_defaults(func=cmd_where)

    p = sub.add_parser("test", help="run the kernel tests and every skill's own")
    p.add_argument("step", nargs="*", help="limit to these steps' skills")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd_test)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except SystemExit:
        raise
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"residual: {exc}", file=sys.stderr)
        return EXIT_FAIL
