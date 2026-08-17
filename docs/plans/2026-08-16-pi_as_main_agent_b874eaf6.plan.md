---
name: Pi as main agent
overview: Make Pi a first-class main agent by sharing the agent-neutral global instructions between Claude and Pi, porting the three enforcement hooks to Pi as a thin extension that reuses the existing hook scripts, and fixing the now-stale local-ai test that pins Pi to local models only.
todos:
  - id: split-claude-md
    content: Create files/claude/rules/conventions.md with the agent-neutral core and trim files/claude/CLAUDE.md to Claude-only mechanics
    status: pending
  - id: pi-agents-md
    content: Add Ansible task symlinking conventions.md to ~/.pi/agent/AGENTS.md
    status: pending
  - id: pi-guardrails-extension
    content: Write files/pi/extensions/guardrails.ts adapter invoking the three hook scripts, with Pi-native skill detection for git-skill-gate
    status: pending
  - id: ansible-extensions-wiring
    content: Add ~/.pi/agent/extensions dir and fileglob symlink task for pi extensions
    status: pending
  - id: fix-local-ai-test
    content: Relax test_local_ai.py settings pins to a subset assertion on the four stable aliases
    status: pending
  - id: docs
    content: Update roles/ai/README.md and repo CLAUDE.md/AGENTS.md for the rules split and Pi guardrails
    status: pending
  - id: verify
    content: Run make test; hand off make check-role ROLE=ai and a manual pi smoke test
    status: pending
isProject: false
---

# Pi as main agent, sharing Claude's setup

## Current state (review summary)

Already working on both agents:

- Pi installed via brew; `settings.json`, `models.json`, `SYSTEM.md`, themes symlinked into `~/.pi/agent/` by [roles/ai/tasks/main.yml](roles/ai/tasks/main.yml)
- All skills shared: `~/.pi/agent/skills` -> `files/claude/skills` (Pi follows the same Agent Skills standard, so `/skill:commit`, `/skill:pr` etc. already exist in Pi). Kept as-is per your decision.
- Project instructions: Pi natively reads `CLAUDE.md`/`AGENTS.md` from cwd and parents, so per-repo context already works
- `local-ai` stable aliases, offline Ollama policy, `pi-review` + `plannotator` packages

Claude-only with no Pi counterpart today:

- Global instructions (`~/.claude/CLAUDE.md` + `~/.claude/rules/*.md`); Pi's one global context file, `~/.pi/agent/AGENTS.md`, is unpopulated
- Enforcement hooks: `em-dash-gate.sh`, `git-skill-gate.sh`, `pre-commit-verify.sh`

Not portable, stays Claude-only (Pi has no subagents/plan mode by design): seat plugins, `architect`/`ux-shaper`, product-team pipeline, `plan-date-stamp.sh`, `skill-recap.sh`, `cloud-readonly-gate.sh`, statusline, tokencost, herdr, rtk hook.

Broken now: `test_pi_config_exposes_only_stable_aliases_for_model_cycling` in [roles/ai/files/scripts/local-ai/tests/test_local_ai.py](roles/ai/files/scripts/local-ai/tests/test_local_ai.py) pins `defaultProvider == "local"` and exactly four `enabledModels`, but the working-tree [roles/ai/files/pi/settings.json](roles/ai/files/pi/settings.json) defaults to `openai-codex` with Codex/Grok models enabled, so `make test` fails.

## Sharing map after this change

```mermaid
flowchart LR
    subgraph repo [roles/ai/files/]
        conventions[claude/rules/conventions.md new]
        claudemd[claude/CLAUDE.md trimmed]
        codereview[claude/rules/code-review.md]
        skills[claude/skills/]
        hooks[claude/hooks/*.sh]
        piext[pi/extensions/guardrails.ts new]
    end
    subgraph claude [~/.claude/]
        crules[rules/ both files]
        cmd[CLAUDE.md]
        chooks[hooks/]
        cskills[skills/ curated by sync]
    end
    subgraph pi [~/.pi/agent/]
        pagents[AGENTS.md]
        pskills[skills/ full share]
        pext[extensions/]
    end
    conventions --> crules
    conventions --> pagents
    codereview --> crules
    claudemd --> cmd
    skills --> cskills
    skills --> pskills
    hooks --> chooks
    hooks -. invoked by .-> piext
    piext --> pext
```



## 1. Split the global instructions

Create `roles/ai/files/claude/rules/conventions.md` holding the agent-neutral core moved out of [roles/ai/files/claude/CLAUDE.md](roles/ai/files/claude/CLAUDE.md):

- Tools & CLIs table and the ctx7 docs-first rule (generalizing the one Claude-specific clause about `claude-api`/`claude-code-guide`)
- Code standards: complete code, comment policy, ADR shape, no hardcoded values, doc length, em/en dash ban, semantic line breaks, wrap width, `docs/plans/` location
- Git conventions: Conventional Branch naming, commits/pushes through the `commit`/`pr` skills (phrased so it reads correctly as `/commit` in Claude and `/skill:commit` in Pi), no attribution lines

`CLAUDE.md` keeps only what is Claude-mechanics: the `attribution` setting note, plan-date-stamp/plan-mode bullets, sandbox and acli behavior, hook-enforcement phrasing.

No Ansible change needed on the Claude side: the existing rules glob task in [roles/ai/tasks/main.yml](roles/ai/tasks/main.yml) already links every `files/claude/rules/*.md` into `~/.claude/rules/`, which loads with the same priority as `CLAUDE.md`. Claude behavior is unchanged.

`code-review.md` stays Claude-only for now (it routes to seat plugins and `/code-review` levels that do not exist in Pi; Pi has `pi-review` installed).

## 2. Give Pi the shared instructions

New task in [roles/ai/tasks/main.yml](roles/ai/tasks/main.yml): symlink `files/claude/rules/conventions.md` -> `~/.pi/agent/AGENTS.md` (same precedent as the skills share: Pi reads Claude's file directly, no second copy). Pi concatenates it with project-level `CLAUDE.md`/`AGENTS.md` automatically. `SYSTEM.md` stays as-is (harness rules).

## 3. Port the three enforcement hooks as one Pi extension

New `roles/ai/files/pi/extensions/guardrails.ts`, a thin adapter, with the logic staying in the already-tested Python hook scripts:

- Listens on Pi `tool_call` events for `write`, `edit`, `bash`
- Builds Claude-hook-compatible JSON (`tool_name` mapped to `Write`/`Edit`/`Bash`, `tool_input` fields mapped from Pi's tool args, `cwd`), spawns the corresponding script from this checkout, blocks the tool call with the script's stderr when it exits 2
- `em-dash-gate.sh` and `pre-commit-verify.sh` work unchanged (neither needs a transcript)
- `git-skill-gate.sh`: the hard blocks (`--no-verify`, attribution lines and dashes in commit messages, staged `.claude/tasks/`) work unchanged; the skill-window check reads Claude's `attributionSkill`, which Pi does not have. The extension does the Pi-side equivalent natively: detect whether `/skill:commit` / `/skill:pr` was invoked in the current session (Pi exposes session messages to extensions) and block gated commands itself when not. If that marker proves unreliable during implementation, v1 falls back to hard-blocks-only in Pi, stated in the extension header.

Wiring in [roles/ai/tasks/main.yml](roles/ai/tasks/main.yml): add `~/.pi/agent/extensions` to the directories task and add a fileglob symlink task for `files/pi/extensions/*.ts`, mirroring the themes task. Pi auto-discovers extensions there; no settings.json change.

## 4. Fix the stale local-ai test

In [roles/ai/files/scripts/local-ai/tests/test_local_ai.py](roles/ai/files/scripts/local-ai/tests/test_local_ai.py), change `test_pi_config_exposes_only_stable_aliases_for_model_cycling` to assert the four stable `local/...` aliases are a subset of `enabledModels` (the invariant local-ai actually needs), dropping the `defaultProvider`/`defaultModel` equality pins that contradict Pi-as-main-agent. `test_pi_models_have_matching_32k_and_64k_stable_profiles` stays as-is.

## 5. Docs

- [roles/ai/README.md](roles/ai/README.md): document the AGENTS.md share, the guardrails extension, and that Pi is a first-class agent
- Repo [CLAUDE.md](CLAUDE.md) / [AGENTS.md](AGENTS.md): note the rules split (agent-neutral conventions vs Claude-only mechanics) and the Pi extension

## Verification

- `make test` (unattended) covers the hook scripts and the fixed local-ai test
- `make check-role ROLE=ai` for the new symlink tasks (needs vault password, run by you)
- Manual: launch `pi` in a repo, confirm the startup header lists AGENTS.md + the extension, then try a raw `git commit` and an em dash write to see the blocks

## Out of scope (noted for later)

- Statusline extension for Pi, tokencost over Pi sessions (`~/.pi/agent/sessions/` JSONL has token/cost data), curating Pi's skill list, sharing `code-review.md` with Pi
- `SYSTEM.md` currently replaces Pi's default system prompt entirely; `APPEND_SYSTEM.md` would append instead. Left as-is, flag if you want it changed.

