# Postgres Docker MCP setup

This artifact installs a secret-free MCP definition that starts Postgres MCP Pro in restricted
mode. The connection URI remains outside the payload, harness JSON, AART state, command arguments,
logs, and receipts.

## Guided setup on macOS

1. Install Docker Desktop and start its daemon.
2. Create a dedicated PostgreSQL role with access only to the database and objects the agent needs.
   Prefer read-only grants even though restricted mode also constrains server behavior.
3. Build a PostgreSQL connection URI following the
   [official URI syntax](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING-URIS).
4. Paste that URI only into the hidden Keychain prompt.
5. Review the digest-pinned image pull, Keychain item, `~/.zshrc` managed block, and restart notice
   separately. Each effect defaults to declined.
6. Open a new shell and restart Claude Code, OpenCode, or Tabnine CLI.

AART stores the URI as the generic-password item `aart/mcp/postgres-docker` with account `default`.
The managed shell block contains only a `/usr/bin/security` lookup. The container receives
`DATABASE_URI` at runtime; database-side permissions remain the primary security boundary.

## Verify

Confirm Docker has the reviewed image without printing the URI:

```sh
docker image inspect 'crystaldba/postgres-mcp@sha256:dbbd346860d29f1543e991f30f3284bf4ab5f096d049ecc3426528f20b1b6e6b' >/dev/null
test -n "${DATABASE_URI:-}"
```

Restart the harness and inspect its MCP status. The installed server key is `postgres`, and the
container command includes `--access-mode=restricted`.

On Linux the MCP JSON remains installable, but setup protocol v1 has no Linux secret-store adapter.
Use your platform's credential manager outside AART and keep the connection URI out of committed
configuration.
