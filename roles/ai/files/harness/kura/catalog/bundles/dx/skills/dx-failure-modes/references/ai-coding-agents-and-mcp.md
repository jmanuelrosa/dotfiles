# AI coding agents and MCP

When to read: the brief or diff touches AI coding agent settings and permissions, MCP server config, agent sandboxes, context exclusion or rules files, or an agent-authored change to dependencies, tests, or build files.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Credentials written into agent or MCP config.** A token or API key stored in an MCP config or agent settings file is read by every tool that loads it and lands in the repo the first time that file is committed.
  Check: agent and MCP config files contain no token values; servers receive credentials from environment references or the OS secure store.
- **MCP server unpinned or unvetted.** A server entry resolving to the latest release of an unreviewed package can swap its tool definitions after approval (a rug pull), and the whole tool schema is an injection surface.
  Check: third-party servers in the project's agent config come from an allowlisted source, their package names match the real publisher, and they are pinned to an exact version, so a changed tool definition arrives as a reviewed diff rather than a silent update.
- **Local MCP server with host-wide reach.** A local server launched with the developer's full filesystem and network turns one poisoned tool call into access to everything the user can read.
  Check: the launch config limits filesystem access to the directories the server needs and disables network unless it needs it; a stdio transport removes the listening port, not the reach.
- **Agent running with the developer's credentials.** An agent whose shell can read SSH keys, cloud CLI config, or credential stores can exfiltrate them on a single injected instruction.
  Check: the agent's sandbox or permission config denies reads of credential paths and keys, arbitrary command execution happens only inside that sandbox, and no production credential, deploy key, or org secret is reachable from it.
- **Secrets readable as agent context.** VCS ignore files do not apply to AI tools, so env files and private keys in the tree get sent to the provider as ordinary context.
  Check: the tool's context-exclusion list covers env files, private keys, and credential or service-account files.
- **Unrestricted agent egress or resources.** An agent runtime with open network and no limits can exfiltrate anything it reads and exhaust the host on a runaway loop.
  Check: the runtime's network policy is allowlist-based, and its container or VM config sets CPU, memory, disk, and process limits.
- **Permission bypass shipped as a shared default.** Auto-accept or skip-permission modes in committed settings apply to every clone, including the unfamiliar code where they are most dangerous.
  Check: committed agent settings enable no permission bypass, auto-accept, or auto-connection of project-declared servers; personal opt-ins stay in uncommitted local settings.
- **Rules files that weaken controls.** Agent rules files are instructions every session obeys, so a directive to skip review, ignore file patterns, or disable a safety feature disarms the agent for the whole repo.
  Check: rules files the change loads or depends on carry no such directive; changes to them go to the caller as proposals in the report, and the ownership rule covering them is the platform seat's (ci-pipelines).
- **Agent edits to files that execute on their own.** An agent-authored change to an install script, task-runner target, hook, test setup, or lockfile runs at the next install or build, before anyone reads it.
  Check: every file in an agent-authored diff is inside the brief's scope; changes to self-executing files are listed individually with any added download, network call, or shell execution flagged; new dependencies pass the name and install-script check in dependencies-and-package-exports, and the dependency audit fails on known vulnerabilities whoever chose the version.

## Escalation triggers (`needs-decision`)

- Adding an MCP server or AI tool integration to shared project config.
- Enabling any permission bypass or auto-accept mode in committed settings.
- Sending a sensitive or regulated repository's content to a hosted AI provider without a recorded decision.

## What good looks like

- Agent and MCP config is committed without secrets, pinned, and reviewed like any other dependency.
- The agent runs sandboxed, with credentials, egress, and resources bounded by config rather than by trust.
- Rules files are reviewed like code and never the place where a safety control is switched off.
- Agent-authored diffs get the same scope and supply-chain checks as human ones, with self-executing files read line by line.
