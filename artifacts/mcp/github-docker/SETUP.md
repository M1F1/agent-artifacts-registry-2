# Install GitHub Docker MCP with AART

This artifact installs GitHub's official Docker-based MCP server for Claude Code, OpenCode, or
Tabnine. The payload merged into the selected harness is secret-free. Its separate macOS setup
wizard pulls the reviewed container image, stores a real GitHub token in Keychain, and adds only a
Keychain lookup to `~/.zshrc`.

The instructions below use Claude Code with User scope, which makes the MCP available in every
Claude Code project on the machine. Choose Project scope instead when the configuration should live
only in one repository.

## What the installation changes

For Claude Code with User scope, AART:

- merges the `github` server definition into `~/.claude.json`;
- pulls
  `ghcr.io/github/github-mcp-server@sha256:881b53d6f75f69bdbc1b5b10fc2f1361717c19054143b3a8529fb5c32061a50e`;
- stores the PAT in macOS Keychain under service `aart/mcp/github-docker` and account `default`;
- adds an owned block to `~/.zshrc` that reads the token from Keychain into
  `GITHUB_PERSONAL_ACCESS_TOKEN`; and
- records non-secret installation/setup receipts so the operation can be inspected and retried.

The token is never written into the registry, artifact payload, harness JSON, AART state, command
arguments, logs, or receipts.

## 1. Install the tested AART release

AART requires Python 3.10 or newer and has no runtime Python dependencies. `pipx` keeps the CLI in
an isolated environment while making `aart` available on `PATH`.

```sh
python3 --version
python3 -c 'import platform; assert platform.mac_ver()[0], "Python cannot detect macOS"'
pipx ensurepath
pipx install --force --python "$(command -v python3)" \
  https://github.com/M1F1/agent-artifacts/releases/download/v2.0.0/agent_artifacts-2.0.0-py3-none-any.whl
exec zsh -l
aart --version
```

Expected version:

```text
agent-artifacts 2.0.0
```

If `pipx` is not installed, install it using the package manager approved for your machine before
continuing. AART itself does not require PyYAML or another runtime package.

If pip fails in `pip._vendor.truststore._macos` or `pip._vendor.packaging.tags` while parsing an
empty macOS version, `pipx` selected a Python interpreter whose `platform.mac_ver()` is broken.
Select another installed Python 3.10+ explicitly. For example, replace the path below with the
absolute path printed by a working interpreter manager:

```sh
pipx install --force \
  --python /absolute/path/to/working/python3 \
  https://github.com/M1F1/agent-artifacts/releases/download/v2.0.0/agent_artifacts-2.0.0-py3-none-any.whl
```

Do not disable certificate validation. The `legacy-certs` option can bypass the first truststore
traceback but cannot repair platform-tag generation when the selected interpreter reports an empty
macOS version.

## 2. Start Docker

Install Docker Desktop if it is not already present. Start it and wait until the daemon is ready:

```sh
open -a Docker
docker info >/dev/null && echo "Docker is ready"
```

Do not pull an unpinned tag manually. The setup wizard pulls the reviewed digest shown above.

## 3. Create a least-privilege GitHub token

1. Open [Create a fine-grained personal access token](https://github.com/settings/personal-access-tokens/new).
2. Use a recognizable name such as `aart-github-mcp` and choose a short expiration period.
3. Select the correct resource owner and only the repositories the MCP should access.
4. Grant only the permissions needed by the tools you intend to use. Read access is sufficient for
   read-only repository, issue, and pull-request workflows; grant write access only when the agent
   should perform those mutations.
5. Copy the token once and keep it in a password manager until the setup wizard asks for it.

Do not export the token manually, paste it into a command, put it in `.zshrc`, or commit it to a
repository.

## 4. Add the registry and install through the TUI

Start AART from a terminal:

```sh
aart
```

Choose **User**, open **Sources**, and select **Add source**. Enter:

```text
Alias: community
Kind: registry-git
Location: https://github.com/M1F1/agent-artifacts-registry-2.git
Ref: main
Default registry: Yes
```

Review the source identity and finalize the source addition. Then select:

```text
Harness: Claude
Action: Install
Scope: User
Mode: Copy
Source: community
Artifact: mcp/github-docker
```

Review the resolved destination, source revision, container digest, and setup queue, then choose
**Finalize**. Copy is the recommended request mode for this merge-based MCP configuration.

## 5. Complete the credential/setup wizard

After the secret-free MCP definition is installed, AART leaves the full-screen interface and
reviews setup separately. The installed payload remains installed if setup is declined or fails.

1. If AART requests explicit source authorization, confirm only after checking that the source is
   `https://github.com/M1F1/agent-artifacts-registry-2.git` and the reviewed effects are expected.
2. Finalize the setup queue.
3. Review and approve the digest-pinned Docker pull.
4. Review and approve the Keychain item creation.
5. Paste the real PAT only into the hidden Keychain-owned prompt and press Enter.
6. Review and approve the owned `~/.zshrc` block.
7. Review and approve the restart notice.

Every effect defaults to **No**. Read the displayed target and command before approving it. The
registry may subsequently offer to prepare a redacted usage-report issue; that prompt is optional
and does not affect installation.

## 6. Restart the shell and verify

Open a new terminal, or replace the current shell with a new login shell:

```sh
exec zsh -l
```

Check that the token was loaded without printing it:

```sh
test -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" && echo "GitHub token loaded from Keychain"
```

Never run `echo "$GITHUB_PERSONAL_ACCESS_TOKEN"`.

Confirm that the reviewed image is present:

```sh
docker image inspect \
  'ghcr.io/github/github-mcp-server@sha256:881b53d6f75f69bdbc1b5b10fc2f1361717c19054143b3a8529fb5c32061a50e' \
  >/dev/null && echo "GitHub MCP image is ready"
```

Inspect the AART and Claude Code state:

```sh
aart marketplace status community/mcp/github-docker \
  --profile claude \
  --scope user \
  --json
claude mcp get github
claude mcp list
```

Finally, start Claude Code:

```sh
claude
```

Run `/mcp` in the interactive session. The installed server key is `github`. A safe first test is:

```text
Show my GitHub username and list five repositories I can access. Do not modify anything.
```

## Equivalent CLI flow

The CLI keeps source addition, payload installation, and credential setup as separate operations.
Mutating marketplace commands review only unless `--yes` is supplied.

Add the registry:

```sh
aart source add \
  --alias community \
  --kind registry-git \
  --location https://github.com/M1F1/agent-artifacts-registry-2.git \
  --ref main \
  --default
```

Review and then finalize the secret-free payload installation:

```sh
aart marketplace install community/mcp/github-docker \
  --profile claude \
  --scope user

aart marketplace install community/mcp/github-docker \
  --profile claude \
  --scope user \
  --yes
```

Review and then execute the setup. Explicit untrusted-source authorization is included because the
public registry entry may not be elevated by local organization policy. The setup-effects flag
approves only the effects shown in the immediately preceding review; the Keychain command still
owns the hidden PAT prompt.

```sh
aart marketplace setup community/mcp/github-docker \
  --profile claude \
  --scope user \
  --authorize-untrusted-source

aart marketplace setup community/mcp/github-docker \
  --profile claude \
  --scope user \
  --authorize-untrusted-source \
  --approve-setup-effects \
  --yes
```

If setup remains incomplete, review and run the setup command again. AART verifies the current
artifact, recipe, plan, and existing ownership receipts before applying another effect.

## GitHub Enterprise and Linux

This artifact targets `github.com`. Use the separate `mcp/github-enterprise-docker` artifact for
the reviewed company GitHub Enterprise starter. Do not add a company host or token directly to this
public artifact.

The MCP JSON is installable on Linux, but setup v2 has no Linux secret-store adapter.
Store the token with the credential manager approved for that environment and expose
`GITHUB_PERSONAL_ACCESS_TOKEN` to the shell that starts the MCP host.
