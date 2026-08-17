# Plan files are dated, and committed


`plansDirectory` in [settings.json](../../roles/ai/files/claude/settings.json) points plan mode at `docs/plans/`, and those files are **tracked in git**: a plan is the design record for the change that followed it, which is the same reason the ADRs are tracked. Nothing in `.gitignore` mentions the directory, so this needs no exclusion to keep working; it needs the commits to actually include it.

**Claude Code owns the filename, so the repo can only rename after the fact.** Plan mode generates a slugified prompt prefix plus a random word pair (`right-now-we-save-glimmering-sun.md`) and exposes no setting to date it, which left a directory whose files sort alphabetically into meaningless order with nothing but `stat` to say which came first. [plan-date-stamp.sh](../../roles/ai/files/claude/hooks/plan-date-stamp.sh) is a `PostToolUse` hook on `ExitPlanMode` that prefixes `YYYY-MM-DD-`, matching the shape `.claude/state/research/` already uses. A prefix rather than a suffix, so the names sort chronologically.

Three things about it are load-bearing:

- **`ExitPlanMode` is the only safe moment.** The plan file is written and edited repeatedly while planning (the workflow instructs exactly that), so a rename on `Write` breaks every later `Edit` against the original path. Approval is the first point at which the file is final.
- **The path comes from the transcript, because the event carries none.** `ExitPlanMode` takes no parameters at all: it reads the plan from the file and passes nothing. Claude Code injects one `attachment` per plan session with `type: "plan_mode"`, holding an absolute `planFilePath` and an `isSubAgent` bool. Reading that is what keeps the hook from parsing `plansDirectory` out of `settings.json`, from needing a `docs/plans` fallback, and from guessing a subagent's plan by matching `-agent-` in its name when a field states it. The last attachment wins, so re-entering plan mode retargets.
- **It fails open and never restamps.** The rename is cosmetic, so every error path exits 0 with no output rather than costing the user an approved plan, and an already-dated name is skipped whatever the date, so a plan revised and re-approved keeps the day it was written.

The hook needs no Ansible change: the symlink task globs `files/claude/hooks/*` with `isfile` filtering, as [claude-kit](../../roles/ai/files/scripts/claude-kit/ARCHITECTURE.md) describes.
