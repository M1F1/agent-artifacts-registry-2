# GitHub Docker MCP setup

This artifact merges a secret-free GitHub MCP server definition into the selected harness. Its
setup wizard is separate from the payload installation and never writes a token into the artifact,
harness JSON, AART state, command arguments, logs, or receipts.

## Guided setup on macOS

1. Install Docker Desktop and make sure the Docker daemon is running.
2. Open the wizard's
   [fine-grained token link](https://github.com/settings/personal-access-tokens/new).
3. Restrict the token to the required repositories and grant only the permissions needed by the
   MCP tools you intend to enable. Organization policy can further restrict token access.
4. Keep the token available only long enough to paste it into the hidden Keychain prompt.
5. Review the digest-pinned image pull, Keychain item, `~/.zshrc` managed block, and restart notice
   separately. Each effect defaults to declined.
6. Open a new shell and restart Claude Code, OpenCode, or Tabnine CLI.

AART stores the token as the generic-password item `aart/mcp/github-docker` with account `default`.
The managed shell block contains only a `/usr/bin/security` lookup. A child process still receives
the resulting environment variable at runtime, so do not enable tools or repository permissions
you do not need.

## Verify

Confirm Docker has the reviewed image without printing the token:

```sh
docker image inspect 'ghcr.io/github/github-mcp-server@sha256:881b53d6f75f69bdbc1b5b10fc2f1361717c19054143b3a8529fb5c32061a50e' >/dev/null
test -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}"
```

Restart the harness and inspect its MCP status. The installed server key is `github`.

This starter targets `github.com`. GitHub Enterprise Server and Enterprise Cloud with data
residency additionally require a reviewed `GITHUB_HOST`; do not put that host or a token directly
into this public artifact.

On Linux the MCP JSON remains installable, but setup protocol v1 has no Linux secret-store adapter.
Follow the same least-privilege guidance and use your platform's credential manager outside AART.
