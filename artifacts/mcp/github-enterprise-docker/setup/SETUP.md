# GitHub Enterprise Docker MCP setup

This artifact installs a secret-free `github-enterprise` MCP definition configured for
`https://github.dev.global.company.org`. It uses a separate local environment variable and
Keychain service, so it does not overwrite the public GitHub MCP credential or server key.

## Guided setup on macOS

1. Configure this registry once, then start the human TUI:

   ```sh
   aart source add \
     --alias community \
     --kind registry-git \
     --location https://github.com/M1F1/agent-artifacts-registry-2.git \
     --ref main \
     --no-default
   aart
   ```

2. In the marketplace, select `community/mcp/github-enterprise-docker`, choose Claude and the
   intended Project or User scope, review the JSON merge, and finalize it. The setup queue opens
   immediately after the payload install.
3. Install Docker Desktop if needed and start its daemon.
4. Open the company GitHub Enterprise
   [personal access token page](https://github.dev.global.company.org/settings/tokens/new).
5. Create a token dedicated to MCP. For a classic token, start with `repo`, `read:org`, and
   `read:user`, then remove any permission your intended MCP tools do not need. Company policy may
   impose additional restrictions.
6. Copy the token and paste it only into the wizard's hidden Keychain prompt. Do not paste it into
   chat, `mcp.json`, `.mcp.json`, Tabnine settings, or this repository.
7. Review the digest-pinned image pull, Keychain item, managed `~/.zshrc` block, and restart notice
   separately. Each effect defaults to declined.
8. Open a new shell and restart Claude Code or Tabnine CLI.

AART stores the token as the generic-password item `aart/mcp/github-enterprise-docker` with account
`default`. The managed shell block exports `GITHUB_ENTERPRISE_PERSONAL_ACCESS_TOKEN` through a
`/usr/bin/security` lookup. At process launch, the harness maps it to the
`GITHUB_PERSONAL_ACCESS_TOKEN` expected by the official image. The token itself is not written to
the artifact, harness JSON, AART state, argv, logs, or receipts.

## Verify without printing the token

```sh
docker image inspect 'ghcr.io/github/github-mcp-server@sha256:881b53d6f75f69bdbc1b5b10fc2f1361717c19054143b3a8529fb5c32061a50e' >/dev/null
test -n "${GITHUB_ENTERPRISE_PERSONAL_ACCESS_TOKEN:-}"
```

For Claude Code, restart Claude and run `/mcp`; the `github-enterprise` server should become ready.
For Tabnine CLI, restart it and run `/mcp` for the same status check.

On Linux the MCP JSON remains installable, but setup protocol v1 has no Linux secret-store adapter.
Use your platform credential manager outside AART and keep the token out of committed configuration.
