# AART Community Registry

Public AART registry containing reviewed skill imports and Docker-based MCP starters:

- all 14 skills from [`obra/superpowers` v6.2.0](https://github.com/obra/superpowers/tree/v6.2.0/skills),
  pinned to commit `3dcbd5c4b48e02263fbf4a3c01e3fe4f81d584d9`;
- `wayfinder`, `grill-with-docs`, and the five skills they invoke from
  [`mattpocock/skills` v1.2.3](https://github.com/mattpocock/skills/tree/v1.2.3), pinned to commit
  `6acc160e4e0cd062dbbbd7a1b26ae92855edf07e`;
- GitHub's official MCP server `v1.9.0`, using the multi-platform image index pinned to
  `sha256:881b53d6f75f69bdbc1b5b10fc2f1361717c19054143b3a8529fb5c32061a50e`,
  published as separate public GitHub and company GitHub Enterprise starters;
- Postgres MCP Pro `v0.3.0`, using its multi-platform image index pinned to
  `sha256:dbbd346860d29f1543e991f30f3284bf4ab5f096d049ecc3426528f20b1b6e6b`.

Every artifact is independently installable. The registry also publishes four collections:

- `superpowers` — the complete skill directory from the reviewed Superpowers release;
- `matt-planning` — Wayfinder and Grill with Docs together with `domain-modeling`, `grilling`,
  `prototype`, `research`, and `setup-matt-pocock-skills`;
- `agent-power-pack` — both skill collections, deduplicated into 21 skills;
- `docker-mcp-starters` — public GitHub, company GitHub Enterprise, and restricted PostgreSQL MCP
  definitions, each with its own setup wizard.

The Superpowers collection contains the skill payloads, including their in-tree scripts and
references. It does not claim to reproduce the upstream plugin bootstrap, hooks, or executable
delivery. AART provides source structure, marketplace discovery, and Copy/Symlink installation;
the skills and their consuming harnesses own runtime behavior.

## Docker MCP starters and credential wizards

`mcp/github-docker`, `mcp/github-enterprise-docker`, and `mcp/postgres-docker` merge only their
secret-free server definitions into supported harness configuration. All payloads use an immutable
image digest. The public GitHub starter targets `github.com`; the enterprise starter targets
`https://github.dev.global.company.org` under a non-conflicting `github-enterprise` server key; the
PostgreSQL starter opts into restricted access mode. The enterprise starter supports Claude Code
and Tabnine without requiring changes to AART.

Each artifact owns a separate `setup/installer.json` and `setup/SETUP.md`. In the human TUI, setup
shows the credential/help links, exact image pull, Keychain item, managed shell block, and restart
notice before applying anything. Consent is per effect and defaults to No. The macOS Keychain tool
owns the hidden prompt: secret values never enter the artifact, harness JSON, AART plan/state,
argv, logs, or receipts. The generated `~/.zshrc` block contains only a Keychain lookup.

Agents retain the non-interactive Review/Finalize split. They can review the payload and setup in
JSON, but setup effects require explicit authorization and approval flags; no flag silently accepts
a credential or effect. Declining or failing setup does not undo a successful MCP JSON install.

The MCP payloads support macOS and Linux. The setup protocol v1 wizard is intentionally macOS-only
because its protected secret channel is Keychain. Linux installation remains available and the
artifact documentation directs users to their platform credential manager rather than storing a
secret in the registry or AART.

## Compatibility and provenance

All packages are first-release registry artifacts at version `1.0.0`, under the upstream MIT
licenses. Their provenance records the exact upstream repository, release, resolved commit, path,
content digest, and—for MCP starters—the reviewed container digest. The seven executable files in
Superpowers preserve their upstream executable mode.

The artifacts do not declare `requires_aart`: none of their payloads depends on an AART executable
capability. The registry remains readable from AART `1.0.0`; CI deliberately compiles and tests it
with released AART `1.3.1` without raising that minimum.

Four artifacts with bundled executable helpers publish advisory runtime requirements: Bash and
Node.js for `brainstorming`, Bash and Git for `subagent-driven-development`, Bash and npm for
`systematic-debugging`, and Node.js plus Graphviz `dot` for `writing-skills`. The example inventory
at `.agent-artifacts/runtime-environment.json` is evaluated in CI with `aart marketplace health`.
These observations remain informational and never block installation.

All three MCP starters similarly advertise Docker as an advisory runtime requirement. A missing Docker
runtime appears in marketplace health and setup preflight; it does not hide the artifact or block
installation of its JSON payload.

## Usage analytics

This registry advertises its own `M1F1/agent-artifacts-registry-2` GitHub Issues endpoint. AART
`1.3.0+` prompt mode routes only this registry's artifact results here, while artifacts installed
from another registry are reported to that registry's endpoint. Source aliases never enter the
payload, identical endpoints are deduplicated, and users retain both default-No confirmations.

Validation and dashboard generation are pinned separately to AART `v1.2.0` through
`AART_ANALYTICS_REF`, so advancing the registry quality tool does not silently alter analytics
output. Reporting failures never affect installation.

## Quality gates

CI uses AART itself to run format, strict/frozen validate, lock, build, audit, and minimum/latest
compatibility gates. It then installs `agent-power-pack` into clean Copy and managed Symlink layouts
and verifies all 21 skills, provenance, license, compatibility, executable modes, and advisory
runtime health. It also installs all three MCP definitions in Copy and Symlink requests, checks the
resulting harness JSON, reviews every setup queue, and executes all declarative wizards against
fake Docker and Keychain adapters with a synthetic secret-leak canary. CI never uses a real token,
database URI, Keychain item, or image pull.
