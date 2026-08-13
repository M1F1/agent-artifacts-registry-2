#!/usr/bin/env sh
# Restart loop: one work unit per agent process.
#
# Each iteration starts a fresh agent with a cold context. That is not a
# consolation prize for harnesses without subagents -- it is the strongest of
# the three execution modes, because blind generators are exactly what random
# simulation depends on. Nothing leaks between units except the files on disk.
#
# The loop terminates when `residual next` exits non-zero, which happens when
# the queue is drained. It stops on convergence, not on a budget.
#
# Usage:
#   skills/residual-run-loop/scripts/loop.sh 03-stressors "claude -p"
#   skills/residual-run-loop/scripts/loop.sh 03-stressors "codex exec"
#
# The agent command is given the prompt on stdin. Override PROMPT_FILE if your
# agent needs a path argument instead; see the variant at the bottom.

set -eu

STEP="${1:-}"
AGENT="${2:-${RESIDUAL_AGENT:-}}"
PROMPT_FILE="${PROMPT_FILE:-.residuality/unit.md}"

# The kernel ships inside the `using-residues` skill, which is this skill's
# sibling both in the framework repo and wherever the two were installed. Fall
# back to an installed `residual` on the PATH, then to the module.
HERE=$(CDPATH= cd -L "$(dirname "$0")" && pwd -L)
SIBLING="$HERE/../../using-residues/kernel/bin/residual"
if [ -z "${RESIDUAL:-}" ]; then
  if [ -x "$SIBLING" ]; then
    RESIDUAL="$SIBLING"
  elif command -v residual >/dev/null 2>&1; then
    RESIDUAL="residual"
  else
    RESIDUAL="python3 -m residual"
  fi
fi

if [ -z "$STEP" ] || [ -z "$AGENT" ]; then
  echo "usage: $0 <step> <agent-command>" >&2
  echo "   eg: $0 03-stressors \"claude -p\"" >&2
  exit 2
fi

mkdir -p "$(dirname "$PROMPT_FILE")"

$RESIDUAL plan "$STEP"

units=0
while $RESIDUAL next --step "$STEP" --out "$PROMPT_FILE" >/dev/null 2>&1; do
  units=$((units + 1))
  printf '\n--- unit %d ---\n' "$units"

  # A fresh process per unit: this is where the context gets cleared.
  $AGENT < "$PROMPT_FILE" || echo "agent exited non-zero; unit stays claimed and will be reclaimed after its TTL" >&2
done

printf '\nqueue drained after %d unit(s)\n' "$units"

$RESIDUAL compile "$STEP"
$RESIDUAL report "$STEP" || true
$RESIDUAL gate "$STEP"

# --- variant: agents that take a file path rather than stdin ---------------
# while $RESIDUAL next --step "$STEP" --out "$PROMPT_FILE" >/dev/null 2>&1; do
#   $AGENT "$PROMPT_FILE"
# done
