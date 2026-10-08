---
name: cc-fewer-permission-prompts
description: Mine Claude Code and Pi transcripts for the read-only shell commands and MCP tools that keep prompting, rank them, and add the ones the user picks to the shared permission policy (policy/permissions.toml) that every harness is rendered from. Use when the user asks for fewer permission prompts or wants to pre-approve safe commands.
argument-hint: "[--min-count N] [--top N] [--sessions N]"
disable-model-invocation: true
---

# Fewer permission prompts

A port of Claude Code's `/fewer-permission-prompts` onto the neutral policy.
Instead of `.claude/settings.json`, the rules go into `policy/permissions.toml`, the single source `make harness` renders into Claude Code, Pi and Codex.
That holds wherever this runs: outside the dotfiles repo it still edits that file, never a project's settings.

The bundled `scripts/mine.py` does the counting, beside this file (global install `~/.claude/skills/cc-fewer-permission-prompts/` or `~/.agents/skills/cc-fewer-permission-prompts/`).
It reads the most recent Claude Code transcripts (`~/.claude/projects/**/*.jsonl`) and Pi sessions (`~/.pi/agent/sessions/**/*.jsonl`), reduces each shell call to its command and read-only subcommand, keeps only what it can show is read-only, and subtracts what the policy already allows or denies and what Claude Code never prompts for.

## Steps

1. **Mine** (single call): `python3 <skill dir>/scripts/mine.py --json`, appending any arguments the user passed (`--min-count`, default 3; `--top`, default 20; `--sessions`, recent transcripts per harness, default 50, `0` for all).
   The JSON carries `policy` (the absolute path of the file to edit), `candidates` (ranked: `pattern`, `count`, `section`, `sources` per harness) and `skipped` (calls per reason, with the top patterns).
   A non-zero exit means the policy file was not found: relay the error and stop.

2. **Present** the candidates as a markdown table, one row each, with a one-line note you write from the pattern:

   | # | Pattern | Count | Section | Notes |
   |---|---------|-------|---------|-------|
   | 1 | `brew info *` | 42 | `commands.allow` | Homebrew package details |
   | 2 | `mcp__claude_ai_Slack__slack_read_channel` | 9 | `tools.allow` | Slack channel reads |

   If `candidates` is empty, say so, summarise `skipped`, and stop.

3. **Vet** each candidate before offering it; the script is the first filter and you are the second.
   Drop, and say why, anything that fails a rule below even though the script proposed it.

4. **Ask** which rules to take: `AskUserQuestion` with `multiSelect: true`, one option per candidate up to the tool's limit (in Pi, the equivalent question tool, or a plain question naming ranks).
   Nothing is written without an answer, and "none" ends the run.

5. **Edit** the file at `policy` from step 1, and only these two arrays:
   - shell patterns go at the end of `[commands] allow`;
   - MCP tool names go at the end of `[tools] allow`.

   Keep the existing shape: one `  "pattern",` per line, two-space indent, trailing comma.
   Skip a pattern already present, remove nothing, reorder nothing, and never touch `deny`, `[paths]`, `[mcp]` or any other section.

6. **Report**: what was added (count and a few examples), what was already covered (`skipped.policy-allowed`), and what was skipped and why, from `skipped` (for example "dropped `python3` and `npm run`: arbitrary code; dropped `git status` and `ls`: Claude Code never prompts for them").
   Then tell the user to run, from the dotfiles checkout that holds the policy file:
   - `make harness`, with no Claude Code session open, since it rewrites Claude's `settings.json`;
   - `make harness-check`, to confirm nothing drifted.

   Never run `make harness` yourself: this session is a Claude Code session or may be one.

## Rules

- **Read-only only.** Nothing that writes, deletes, renames, pushes, merges, installs, deploys, or runs a build or test with side effects. When in doubt, leave it out.
- **Never a pattern that grants arbitrary code execution.** That covers interpreters (`python3`, `node`, `bun`, `deno`, `ruby`, `perl`, `awk`), shells (`bash`, `sh`, `zsh`, `fish`, `eval`, `exec`, `ssh`), package runners (`npx`, `bunx`, `uvx`, `uv run`), task-runner wildcards (`npm run *`, `pnpm run *`, `make *`, `just *`, `cargo run *`, `go run *`), tools that start an interpreter in the working directory (`pyright`), and `gh api *`, `docker run` or `exec`, `kubectl exec`, `sudo`, `xargs`, plus anything with `-exec`. An exact `bun run typecheck` is fine; `bun run *` is not.
- **Never a secret reader.** No `op`, `security`, `vault`, `pass`, or any subcommand naming a token, secret, password or credential.
- **Narrowest pattern that covers the usage.** Many variants become `cmd sub *`, with the space before `*`; a single repeated invocation stays exact with no wildcard; an MCP tool is its full name, verbatim. Never widen a pattern past the rules above.
- **Skip what Claude Code already auto-allows**: `cat`, `head`, `tail`, `ls`, `echo`, `grep`, `rg`, `find`, `sed`, `jq`, `which`, read-only `git`, `gh` and `docker` subcommands, and the rest of its validated list. The script drops them; do not add them back.
- Pi's own bash and MCP fallbacks already allow, so these rules mostly spare Claude Code and Codex prompts. The edit is still made once, in the neutral policy.
- Never add to `deny`, and never edit a rendered file (`adapters/*/settings.json`, Pi's `permissions.json`, Codex's `config.toml`) directly.
