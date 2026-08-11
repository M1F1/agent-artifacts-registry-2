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
mcp_starters = {
    "github-docker": {
        "server_name": "github",
        "environment": "GITHUB_PERSONAL_ACCESS_TOKEN",
        "image": "ghcr.io/github/github-mcp-server@sha256:881b53d6f75f69bdbc1b5b10fc2f1361717c19054143b3a8529fb5c32061a50e",
        "service": "aart/mcp/github-docker",
        "origin_url": "https://github.com/github/github-mcp-server.git",
        "origin_commit": "cdfa34e0a9d3e1ae6825345471f25185dd61d74e",
    },
    "postgres-docker": {
        "server_name": "postgres",
        "environment": "DATABASE_URI",
        "image": "crystaldba/postgres-mcp@sha256:dbbd346860d29f1543e991f30f3284bf4ab5f096d049ecc3426528f20b1b6e6b",
        "service": "aart/mcp/postgres-docker",
        "origin_url": "https://github.com/crystaldba/postgres-mcp.git",
        "origin_commit": "7179ab0336396f819e23b0b012a9c284be10fac3",
    },
}


def collection(name):
    return json.loads((root / "collections" / f"{name}.json").read_text(encoding="utf-8"))


superpowers_collection = collection("superpowers")
matt_collection = collection("matt-planning")
power_pack = collection("agent-power-pack")
mcp_collection = collection("docker-mcp-starters")
if {item["name"] for item in superpowers_collection["artifacts"]} != superpowers:
    raise SystemExit("superpowers collection does not contain the reviewed 14 skills")
if {item["name"] for item in matt_collection["artifacts"]} != matt:
    raise SystemExit("matt-planning does not contain the requested skills and their dependencies")
if set(power_pack["collections"]) != {"superpowers", "matt-planning"}:
    raise SystemExit("agent-power-pack must compose both reviewed collections")
if {
    (item["type"], item["name"]) for item in mcp_collection["artifacts"]
} != {("mcp", name) for name in mcp_starters}:
    raise SystemExit("docker-mcp-starters must contain both reviewed MCP examples")

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

for name, expected_mcp in mcp_starters.items():
    artifact_root = root / "artifacts" / "mcp" / name
    manifest = json.loads((artifact_root / "artifact.json").read_text(encoding="utf-8"))
    if manifest["version"] != "1.0.0" or manifest["license"] != "MIT":
        raise SystemExit(f"mcp/{name} must remain at the reviewed MIT 1.0.0 release")
    if "requires_aart" in manifest:
        raise SystemExit(f"mcp/{name} must not gain an incidental requires_aart bound")
    if set(manifest["compatibility"]["platforms"]) != {"darwin", "linux"}:
        raise SystemExit(f"mcp/{name} has an unexpected platform contract")
    if set(manifest["compatibility"]["profiles"]) != {"claude", "opencode", "tabnine"}:
        raise SystemExit(f"mcp/{name} has an unexpected profile contract")
    if set(manifest["install"]["modes"]) != {"copy", "symlink"}:
        raise SystemExit(f"mcp/{name} must accept Copy and Symlink installation requests")
    if set(manifest["install"]["scopes"]) != {"project", "user"}:
        raise SystemExit(f"mcp/{name} must support project and user scope")
    if manifest["install"]["effects"] != ["merge-json"]:
        raise SystemExit(f"mcp/{name} must only merge its server definition")
    if manifest["setup"] != {"recipe": "setup/installer.json", "platforms": ["darwin"]}:
        raise SystemExit(f"mcp/{name} must declare its own macOS setup wizard")
    declared = manifest.get(runtime_extension, {})
    if {item["id"] for item in declared.get("requirements", [])} != {"command.docker"}:
        raise SystemExit(f"mcp/{name} must advertise Docker as advisory runtime metadata")

    payload = json.loads((artifact_root / "payload" / "mcp.json").read_text(encoding="utf-8"))
    server = payload["server"]
    if payload["name"] != expected_mcp["server_name"] or server["command"] != "docker":
        raise SystemExit(f"mcp/{name} has an unexpected installed server identity")
    if server["args"][-1] != expected_mcp["image"] and name == "github-docker":
        raise SystemExit("GitHub MCP must run the reviewed digest-pinned image")
    if expected_mcp["image"] not in server["args"]:
        raise SystemExit(f"mcp/{name} must run the reviewed digest-pinned image")
    environment_name = expected_mcp["environment"]
    if server["env"] != {environment_name: "${" + environment_name + "}"}:
        raise SystemExit(f"mcp/{name} payload must contain only an environment lookup")
    if name == "postgres-docker" and "--access-mode=restricted" not in server["args"]:
        raise SystemExit("Postgres MCP must default to restricted access mode")

    installer = json.loads(
        (artifact_root / "setup" / "installer.json").read_text(encoding="utf-8")
    )
    if installer["artifact"] != f"mcp/{name}" or installer["platforms"] != ["darwin"]:
        raise SystemExit(f"mcp/{name} setup identity or platform is incorrect")
    if set(installer["capabilities"]) != {
        "keychain",
        "filesystem",
        "docker",
        "network",
        "process",
    }:
        raise SystemExit(f"mcp/{name} setup capabilities are not least-bounded")
    if len(installer["inputs"]) != 1 or installer["inputs"][0]["type"] != "secret":
        raise SystemExit(f"mcp/{name} must have one hidden credential input")
    if any(not item["url"].startswith("https://") for item in installer["help_urls"]):
        raise SystemExit(f"mcp/{name} has a non-HTTPS wizard help link")
    steps = {step["use"]: step["with"] for step in installer["steps"]}
    if steps["docker.pull@1"]["image"] != expected_mcp["image"]:
        raise SystemExit(f"mcp/{name} setup pull and runtime images differ")
    keychain = steps["macos-keychain.store@1"]
    if keychain["service"] != expected_mcp["service"]:
        raise SystemExit(f"mcp/{name} must own a separate Keychain item")
    lookup = steps["shell.env-from-keychain@1"]["variables"]
    if lookup[environment_name]["service"] != expected_mcp["service"]:
        raise SystemExit(f"mcp/{name} shell lookup and Keychain service differ")
    if not (artifact_root / "setup" / "SETUP.md").is_file():
        raise SystemExit(f"mcp/{name} is missing its human setup guide")

    provenance = json.loads((artifact_root / "provenance.json").read_text(encoding="utf-8"))
    origin = provenance["origin"]
    container = provenance["com.m1f1.container-source"]
    if (
        origin["url"] != expected_mcp["origin_url"]
        or origin["resolved_commit"] != expected_mcp["origin_commit"]
        or "@" + container["image_digest"] not in expected_mcp["image"]
    ):
        raise SystemExit(f"mcp/{name} has unexpected upstream or image provenance")

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
from agent_artifacts.consumer.model import ConsumerActionRequest
from agent_artifacts.consumer.runtime import load_local_consumer_service
from agent_artifacts.domain.result import Ok
from agent_artifacts.model import Ok as LegacyOk
from agent_artifacts.model import Request, SetupQueueItem
from agent_artifacts.setup import parse_installer, plan_setup
from agent_artifacts.setup_runtime import ProcessResult, SetupRuntime, apply_setup_plan

registry = Path(sys.argv[1])
test_root = Path(sys.argv[2])
user_home = test_root / "home"
user_home.mkdir()
canary = "aart-secret-canary-must-never-escape"


def run(command, request):
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = command(request)
    payload = json.loads(stdout.getvalue())
    if code != 0 or payload.get("ok") is not True:
        raise SystemExit(payload)
    return payload


class FakeSetupProcess:
    def __init__(self):
        self.calls = []
        self.keychain = set()
        self.images = set()

    def __call__(self, argv, *, env, cwd, timeout, capture):
        args = tuple(argv)
        self.calls.append((args, dict(env), cwd, timeout, capture))
        if "find-generic-password" in args:
            identity = (args[args.index("-s") + 1], args[args.index("-a") + 1])
            return ProcessResult(0 if identity in self.keychain else 44)
        if "add-generic-password" in args:
            identity = (args[args.index("-s") + 1], args[args.index("-a") + 1])
            self.keychain.add(identity)
            return ProcessResult(0)
        if "delete-generic-password" in args:
            identity = (args[args.index("-s") + 1], args[args.index("-a") + 1])
            self.keychain.discard(identity)
            return ProcessResult(0)
        if args[:3] == ("docker", "image", "inspect"):
            return ProcessResult(0 if args[3] in self.images else 1)
        if args[:2] == ("docker", "pull"):
            self.images.add(args[2])
            return ProcessResult(0)
        return ProcessResult(0)


fake_setup = FakeSetupProcess()
wizard_home = test_root / "wizard-home"
wizard_home.mkdir()
wizard_results = []
for name in ("github-docker", "postgres-docker"):
    artifact_root = registry / "artifacts" / "mcp" / name
    parsed = parse_installer(
        (artifact_root / "setup" / "installer.json").read_bytes(),
        artifact_key=f"mcp/{name}",
        descriptor_path="setup/installer.json",
    )
    if not isinstance(parsed, LegacyOk):
        raise SystemExit(parsed)
    item = SetupQueueItem(
        "mcp",
        name,
        "tabnine",
        "project",
        "community",
        str(artifact_root),
        parsed.value,
    )
    plan = plan_setup(
        item,
        target_root=str(wizard_home),
        home_root=str(wizard_home),
        platform="darwin",
    )
    runtime = SetupRuntime(
        process=fake_setup,
        platform="darwin",
        environ={"PATH": "/usr/bin:/bin", "SECRET_CANARY": canary},
        tool_exists=lambda _tool: True,
    )
    configured = apply_setup_plan(plan, runtime, consent=lambda _effect: True)
    repeated = apply_setup_plan(plan, runtime, consent=lambda _effect: True)
    if configured.status != "configured" or repeated.status != "already_configured":
        raise SystemExit(f"mcp/{name} setup is not successful and idempotent")
    wizard_results.extend((configured, repeated))

zshrc = (wizard_home / ".zshrc").read_text(encoding="utf-8")
observable = repr(fake_setup.calls) + repr(wizard_results) + zshrc
if canary in observable:
    raise SystemExit("synthetic secret escaped a setup wizard boundary")
for expected in (
    "aart/mcp/github-docker",
    "GITHUB_PERSONAL_ACCESS_TOKEN",
    "aart/mcp/postgres-docker",
    "DATABASE_URI",
):
    if expected not in zshrc:
        raise SystemExit(f"wizard did not create the reviewed Keychain lookup: {expected}")


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

    service = load_local_consumer_service(project=str(project), user_home=str(user_home))
    if not isinstance(service, Ok):
        raise SystemExit(service)
    coordinates = tuple(
        sorted(
            (
                item.coordinate
                for item in service.value.context.catalog.items
                if item.coordinate.artifact.kind == "mcp"
                and item.coordinate.artifact.name in {"github-docker", "postgres-docker"}
            ),
            key=str,
        )
    )
    reviewed = service.value.prepare(
        ConsumerActionRequest(
            "install",
            coordinates,
            ("claude", "opencode", "tabnine"),
            scope="project",
            mode=mode,
        )
    )
    if not isinstance(reviewed, Ok):
        raise SystemExit(reviewed)
    installed = service.value.finalize(reviewed.value, reviewed.value.review_digest)
    if not isinstance(installed, Ok) or installed.value.session_status != "succeeded":
        raise SystemExit(installed)
    if len(installed.value.items) != 6 or any(
        item.setup_status != "pending" for item in installed.value.items
    ):
        raise SystemExit("every MCP/profile install must queue its own setup review")

    targets = (
        (project / ".mcp.json", "mcpServers"),
        (project / "opencode.json", "mcp"),
        (project / ".tabnine" / "agent" / "settings.json", "mcpServers"),
    )
    for target, key in targets:
        document = json.loads(target.read_text(encoding="utf-8"))
        servers = document[key]
        if set(servers) != {"github", "postgres"}:
            raise SystemExit(f"unexpected MCP merge at {target}: {document!r}")
        if servers["github"]["env"] != {
            "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
        }:
            raise SystemExit("GitHub credential lookup changed during harness merge")
        if servers["postgres"]["env"] != {"DATABASE_URI": "${DATABASE_URI}"}:
            raise SystemExit("Postgres credential lookup changed during harness merge")

setup_review = run(
    marketplace.run,
    Request(
        command="marketplace",
        marketplace_action="setup",
        names=("community/collection/docker-mcp-starters",),
        profiles=("claude", "opencode", "tabnine"),
        project=str(test_root / "copy"),
        scope="project",
        user_home=str(user_home),
        authorize_untrusted_source=True,
        json=True,
    ),
)
planned_setup = setup_review.get("setup", {}).get("planned", [])
if len(planned_setup) != 6:
    raise SystemExit(f"expected one reviewed setup per MCP/profile: {setup_review!r}")
if any(len(item["effects"]) != 4 for item in planned_setup):
    raise SystemExit("each MCP setup must review pull, Keychain, shell, and restart effects")

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

mcp_health = run(
    marketplace.run,
    Request(
        command="marketplace",
        marketplace_action="health",
        names=("community/collection/docker-mcp-starters",),
        runtime_environment=str(registry / ".agent-artifacts" / "runtime-environment.json"),
        project=str(test_root / "copy"),
        user_home=str(user_home),
        json=True,
    ),
)
if mcp_health.get("summary", {}).get("satisfied") != 2:
    raise SystemExit(f"Docker MCP runtime health is not satisfied: {mcp_health!r}")
PY

for mode in copy symlink; do
  project="$TEST_ROOT/$mode"
  test -x "$project/.claude/skills/brainstorming/scripts/start-server.sh"
  test -x "$project/.claude/skills/writing-skills/render-graphs.js"
done

test ! -L "$TEST_ROOT/copy/.claude/skills/brainstorming"
test -L "$TEST_ROOT/symlink/.claude/skills/brainstorming"
