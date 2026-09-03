# Terminal Command Duration Footer: Design Doc

**Status:** Approved
**Author:** Jose Manuel Rosa
**Date:** 2026-09-03
**Scope:** `roles/shell/files/starship.toml`

## Summary

Show the elapsed time of every completed interactive Fish command on its own dim line immediately before the next prompt. Extend the existing Starship command-duration module instead of adding a second timing mechanism.

## Motivation

The shell already enables Starship's `cmd_duration` module, but Starship's default threshold hides commands shorter than two seconds. As a result, timing is absent for most interactive commands even though `$cmd_duration` is already part of the prompt format (`roles/shell/files/starship.toml:9-18`, `roles/shell/files/starship.toml:27-29`).

The desired behavior is consistent and glanceable: after command output finishes, print a subdued `Took 83ms` line, then render the normal directory/Git prompt. The timing should be enabled by default without changing command execution or requiring users to opt in per shell.

## Non-goals

- Time non-interactive Fish scripts or commands run by Ansible.
- Track the eventual completion time of background jobs.
- Replace the `franciscolourenco/done` desktop notification behavior for long commands.
- Add timing support for Bash, Zsh, or application-internal commands.
- Right-align the duration or add terminal-width-dependent layout.

## Background

### Existing prompt today

Fish initializes Starship for interactive sessions in `roles/shell/files/fish/config.fish:1-7`. The Starship format includes `$cmd_duration` alongside directory and Git context, and the module is enabled without overriding its default minimum duration (`roles/shell/files/starship.toml:9-18`, `roles/shell/files/starship.toml:27-29`).

The shell role symlinks this configuration to `~/.config/starship.toml`, so repository edits take effect immediately on a provisioned machine (`roles/shell/tasks/main.yml:179-184`). No Ansible task change is required.

### Long-command notifications

The Fisher `done` plugin remains separate. It uses a 10-second threshold and exclusions for interactive/full-screen commands (`roles/shell/files/fish/config.fish:64-66`). The footer does not change those notifications.

## Design rules

- Starship remains the single terminal rendering and duration-formatting layer.
- Every completed foreground command in an interactive Fish session is eligible, including failed and interrupted commands.
- The duration is placed on its own line before the normal prompt.
- Milliseconds are shown so sub-second commands remain meaningful.
- The footer is visually secondary (`dimmed white`) and has no icon.
- The first prompt in a new shell has no duration footer because no command has completed.
- Existing `done` notification thresholds and exclusions remain unchanged.

This is a deep configuration module: the prompt exposes one small formatting surface while Fish and Starship retain responsibility for measuring commands and passing duration state.

## Design

### 1. Move duration to the start of the prompt

Move `$cmd_duration` from the context row to the beginning of the top-level Starship format:

```toml
format = """
$cmd_duration\
$directory\
$nodejs\
$custom\
$git_branch\
$git_status\
$line_break\
$character"""
```

Starship renders the prompt after command output. Putting this module first makes it the footer for the command that just finished while preserving the existing prompt below it.

### 2. Make the module unconditional and self-terminating

Configure the duration module as follows:

```toml
[cmd_duration]
disabled = false
min_time = 0
show_milliseconds = true
format = "[Took $duration]($style)\n"
style = "dimmed white"
```

The newline belongs inside the module format. When no duration exists, such as the first prompt, Starship omits the whole module and therefore emits no stray blank footer line. This shape was validated against the installed Starship 1.26.0 prompt renderer with and without `--cmd-duration`.

### 3. Preserve surrounding behavior

Keep `add_newline = true`, the prompt character, directory/Git modules, and all Fish hooks unchanged. Long-command desktop notifications continue to use the existing `done` plugin configuration.

## Runtime behaviour matrix

| Situation | Result |
|---|---|
| First prompt in a new shell | Normal prompt; no duration footer |
| Successful foreground command | `Took <duration>` followed by the normal prompt |
| Failed foreground command | Duration still shown; existing prompt status behavior remains |
| Command interrupted with Ctrl-C | Duration still shown when Fish returns to the prompt |
| Sub-second command | Duration shown in milliseconds |
| Multi-second command | Starship formats the duration using its native human-readable representation |
| Background command launch (`cmd &`) | Measures launch/return time, not eventual job completion |
| Full-screen command | Footer appears after the application exits and Fish redraws the prompt |
| Non-interactive Fish process | No Starship prompt and no footer |

## Alternatives considered

- **Fish `fish_postexec` handler:** Rejected because Fish already passes command duration to Starship. A second renderer would duplicate responsibility and create additional formatting and event-order edge cases.
- **Keep duration inline with directory/Git context:** Rejected because the selected layout is a dedicated footer line.
- **Right prompt:** Rejected because it is less stable with long output and narrow terminal widths, and it does not match the selected layout.
- **External timing wrapper:** Rejected because it would alter command invocation and would not naturally cover shell built-ins, aliases, and functions.

## Testing decisions

- Validate the configuration with the installed Starship binary using synthetic `--cmd-duration` values for sub-second and multi-second durations.
- Validate the no-duration case to ensure the first prompt has no stray footer line.
- Open a fresh interactive Fish shell and smoke-test success, failure, Ctrl-C, and a background command.
- Run the repository's unattended test target if implementation changes extend beyond this configuration-only edit.

## Open questions

None. The user selected the dedicated footer-line layout.

## Appendix: affected files

- `docs/design/terminal-command-duration-footer.md`: design record.
- `roles/shell/files/starship.toml`: move and format the existing duration module.
