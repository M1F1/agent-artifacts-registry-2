#!/usr/bin/env sh
set -eu

export PYTHONDONTWRITEBYTECODE=1

REGISTRY_ROOT=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/aart-community-registry.XXXXXX")
TEST_ROOT=$(CDPATH= cd "$TEST_ROOT" && pwd -P)
cleanup() {
  chmod -R u+w "$TEST_ROOT" 2>/dev/null || true
  rm -rf "$TEST_ROOT"
}
trap cleanup EXIT HUP INT TERM

python3 - "$REGISTRY_ROOT" <<'PY'
import json
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
superpowers = {
    "brainstorming",
    "dispatching-parallel-agents",
    "executing-plans",
    "finishing-a-development-branch",
    "receiving-code-review",
    "requesting-code-review",
    "subagent-driven-development",
    "systematic-debugging",
    "test-driven-development",
    "using-git-worktrees",
    "using-superpowers",
    "verification-before-completion",
    "writing-plans",
    "writing-skills",
}
matt = {
    "domain-modeling",
    "grilling",
    "grill-with-docs",
    "prototype",
    "research",
    "setup-matt-pocock-skills",
    "wayfinder",
}
expected = superpowers | matt
runtime_extension = "com.m1f1.runtime-requirements"
expected_runtime_requirements = {
    "brainstorming": {"command.bash", "command.node"},
    "subagent-driven-development": {"command.bash", "command.git"},
    "systematic-debugging": {"command.bash", "command.npm"},
    "writing-skills": {"command.dot", "command.node"},
}


def collection(name):
    return json.loads((root / "collections" / f"{name}.json").read_text(encoding="utf-8"))


superpowers_collection = collection("superpowers")
matt_collection = collection("matt-planning")
power_pack = collection("agent-power-pack")
if {item["name"] for item in superpowers_collection["artifacts"]} != superpowers:
    raise SystemExit("superpowers collection does not contain the reviewed 14 skills")
if {item["name"] for item in matt_collection["artifacts"]} != matt:
    raise SystemExit("matt-planning does not contain the requested skills and their dependencies")
if set(power_pack["collections"]) != {"superpowers", "matt-planning"}:
    raise SystemExit("agent-power-pack must compose both reviewed collections")

for name in expected:
    artifact_root = root / "artifacts" / "skill" / name
    manifest = json.loads((artifact_root / "artifact.json").read_text(encoding="utf-8"))
    if manifest["version"] != "1.0.0" or manifest["license"] != "MIT":
        raise SystemExit(f"skill/{name} must remain at the reviewed MIT 1.0.0 import")
    if "requires_aart" in manifest:
        raise SystemExit(f"skill/{name} must not gain an incidental requires_aart bound")
    declared = manifest.get(runtime_extension)
    expected_runtime = expected_runtime_requirements.get(name)
    if expected_runtime is None and declared is not None:
        raise SystemExit(f"skill/{name} claims an unreviewed runtime requirement")
    if expected_runtime is not None and (
        declared is None
        or {item["id"] for item in declared["requirements"]} != expected_runtime
    ):
        raise SystemExit(f"skill/{name} has unexpected advisory runtime requirements")
    if set(manifest["compatibility"]["platforms"]) != {"darwin", "linux"}:
        raise SystemExit(f"skill/{name} has an unexpected platform contract")
    if set(manifest["compatibility"]["profiles"]) != {
        "claude",
        "opencode",
        "tabnine",
        "vibe",
    }:
        raise SystemExit(f"skill/{name} has an unexpected profile contract")
    if set(manifest["install"]["modes"]) != {"copy", "symlink"}:
        raise SystemExit(f"skill/{name} must support Copy and Symlink")
    if set(manifest["install"]["scopes"]) != {"project", "user"}:
        raise SystemExit(f"skill/{name} must support project and user scope")
    origin = json.loads((artifact_root / "provenance.json").read_text(encoding="utf-8"))["origin"]
    if name in superpowers:
        expected_url = "https://github.com/obra/superpowers.git"
        expected_commit = "3dcbd5c4b48e02263fbf4a3c01e3fe4f81d584d9"
    else:
        expected_url = "https://github.com/mattpocock/skills.git"
        expected_commit = "6acc160e4e0cd062dbbbd7a1b26ae92855edf07e"
    if origin["url"] != expected_url or origin["resolved_commit"] != expected_commit:
        raise SystemExit(f"skill/{name} has unexpected upstream provenance")

for relative in (
    "brainstorming/payload/scripts/start-server.sh",
    "brainstorming/payload/scripts/stop-server.sh",
    "subagent-driven-development/payload/scripts/review-package",
    "subagent-driven-development/payload/scripts/sdd-workspace",
    "subagent-driven-development/payload/scripts/task-brief",
    "systematic-debugging/payload/find-polluter.sh",
    "writing-skills/payload/render-graphs.js",
):
    path = root / "artifacts" / "skill" / relative
    if not os.access(path, os.X_OK):
        raise SystemExit(f"upstream executable mode was lost: {relative}")
PY

python3 - "$REGISTRY_ROOT" "$TEST_ROOT" <<'PY'
import contextlib
import io
import json
import sys
from pathlib import Path

from agent_artifacts.commands import marketplace, source
from agent_artifacts.model import Request

registry = Path(sys.argv[1])
test_root = Path(sys.argv[2])
user_home = test_root / "home"
user_home.mkdir()


def run(command, request):
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = command(request)
    payload = json.loads(stdout.getvalue())
    if code != 0 or payload.get("ok") is not True:
        raise SystemExit(payload)
    return payload


run(
    source.run,
    Request(
        command="source",
        source_action="add",
        source_alias="community",
        source_kind="source-local",
        source_location=str(registry),
        source_make_default=False,
        user_home=str(user_home),
        json=True,
    ),
)

for mode in ("copy", "symlink"):
    project = test_root / mode
    project.mkdir()
    result = run(
        marketplace.run,
        Request(
            command="marketplace",
            marketplace_action="install",
            names=("community/collection/agent-power-pack",),
            profiles=("claude",),
            project=str(project),
            scope="project",
            user_home=str(user_home),
            yes=True,
            json=True,
            install_mode=mode,
        ),
    )
    if len(result.get("items", [])) != 21:
        raise SystemExit(f"unexpected collection install result: {result!r}")

health = run(
    marketplace.run,
    Request(
        command="marketplace",
        marketplace_action="health",
        names=("community/collection/agent-power-pack",),
        runtime_environment=str(registry / ".agent-artifacts" / "runtime-environment.json"),
        project=str(test_root / "copy"),
        user_home=str(user_home),
        json=True,
    ),
)
if health.get("advisory") is not True or health.get("installation_blocking") is not False:
    raise SystemExit("runtime health must remain advisory and installation-nonblocking")
summary = health.get("summary", {})
if summary.get("satisfied") != 4 or summary.get("not-declared") != 17:
    raise SystemExit(f"unexpected runtime health summary: {summary!r}")
if any(summary.get(status) != 0 for status in ("unsatisfied", "unknown", "unavailable", "invalid")):
    raise SystemExit(f"reviewed runtime inventory is not healthy: {summary!r}")
PY

for mode in copy symlink; do
  project="$TEST_ROOT/$mode"
  test -x "$project/.claude/skills/brainstorming/scripts/start-server.sh"
  test -x "$project/.claude/skills/writing-skills/render-graphs.js"
done

test ! -L "$TEST_ROOT/copy/.claude/skills/brainstorming"
test -L "$TEST_ROOT/symlink/.claude/skills/brainstorming"
