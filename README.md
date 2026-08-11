# AART Community Skills Registry

Public AART registry containing reviewed, immutable imports from two MIT-licensed upstreams:

- all 14 skills from [`obra/superpowers` v6.2.0](https://github.com/obra/superpowers/tree/v6.2.0/skills),
  pinned to commit `3dcbd5c4b48e02263fbf4a3c01e3fe4f81d584d9`;
- `wayfinder`, `grill-with-docs`, and the five skills they invoke from
  [`mattpocock/skills` v1.2.3](https://github.com/mattpocock/skills/tree/v1.2.3), pinned to commit
  `6acc160e4e0cd062dbbbd7a1b26ae92855edf07e`.

Every artifact is independently installable. The registry also publishes three collections:

- `superpowers` — the complete skill directory from the reviewed Superpowers release;
- `matt-planning` — Wayfinder and Grill with Docs together with `domain-modeling`, `grilling`,
  `prototype`, `research`, and `setup-matt-pocock-skills`;
- `agent-power-pack` — both collections, deduplicated into 21 skills.

The Superpowers collection contains the skill payloads, including their in-tree scripts and
references. It does not claim to reproduce the upstream plugin bootstrap, hooks, or executable
delivery. AART provides source structure, marketplace discovery, and Copy/Symlink installation;
the skills and their consuming harnesses own runtime behavior.

## Compatibility and provenance

All packages are first-release registry imports at artifact version `1.0.0`, under the upstream MIT
licenses. Their provenance records the exact upstream repository, tag, resolved commit, path, and
content digest. The seven executable files in Superpowers preserve their upstream executable mode.

The artifacts do not declare `requires_aart`: none of their payloads depends on an AART executable
capability. The registry remains readable from AART `1.0.0`; CI deliberately compiles and tests it
with released AART `1.3.0` without raising that minimum.

Four artifacts with bundled executable helpers publish advisory runtime requirements: Bash and
Node.js for `brainstorming`, Bash and Git for `subagent-driven-development`, Bash and npm for
`systematic-debugging`, and Node.js plus Graphviz `dot` for `writing-skills`. The example inventory
at `.agent-artifacts/runtime-environment.json` is evaluated in CI with `aart marketplace health`.
These observations remain informational and never block installation.

## Usage analytics

This registry advertises its own `M1F1/agent-artifacts-registry-2` GitHub Issues endpoint. AART
`1.3.0` prompt mode routes only this registry's artifact results here, while artifacts installed
from another registry are reported to that registry's endpoint. Source aliases never enter the
payload, identical endpoints are deduplicated, and users retain both default-No confirmations.

Validation and dashboard generation are pinned separately to AART `v1.2.0` through
`AART_ANALYTICS_REF`, so advancing the registry quality tool does not silently alter analytics
output. Reporting failures never affect installation.

## Quality gates

CI uses AART itself to run format, strict/frozen validate, lock, build, audit, and minimum/latest
compatibility gates. It then installs `agent-power-pack` into clean Copy and managed Symlink layouts
and verifies all 21 skills, provenance, license, compatibility, executable modes, and advisory
runtime health.
