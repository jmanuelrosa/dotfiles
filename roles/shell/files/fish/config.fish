if not status is-interactive
    return
end

set -U fish_greeting

starship init fish | source

function __starship_humanize_duration --on-event fish_postexec
    set -l duration_ms $CMD_DURATION

    if test $duration_ms -lt 1000
        set -gx STARSHIP_HUMANIZED_DURATION "less than 1s"
        return
    end

    set -l remaining (math --scale 0 "floor($duration_ms / 1000)")
    set -l parts
    set -l days (math --scale 0 "floor($remaining / 86400)")
    set remaining (math "$remaining % 86400")
    set -l hours (math --scale 0 "floor($remaining / 3600)")
    set remaining (math "$remaining % 3600")
    set -l minutes (math --scale 0 "floor($remaining / 60)")
    set -l seconds (math "$remaining % 60")

    test $days -gt 0; and set -a parts "$days"d
    test $hours -gt 0; and set -a parts "$hours"h
    test $minutes -gt 0; and set -a parts "$minutes"m
    test $seconds -gt 0; and set -a parts "$seconds"s

    set -gx STARSHIP_HUMANIZED_DURATION (string join ' ' $parts)
end

zoxide init fish | source
fnm env --use-on-cd | source

fish_add_path $HOME/.local/bin
fish_add_path $HOME/.node/bin
fish_add_path $HOME/.bun/bin
fish_add_path $HOME/.claude

# brew specific paths
fish_add_path /opt/homebrew/sbin
fish_add_path /opt/homebrew/bin

# PSQL specific path
fish_add_path /opt/homebrew/opt/libpq/bin

# Make default programs
set -gx BROWSER open
set -gx FILE spf
set -gx PAGER "bat --plain"
set -gx TERMINAL ghostty
set -gx VISUAL zed
set -gx RIPGREP_CONFIG_PATH "$HOME/.config/ripgrep/config"

# ripgrep options
set -gx RIPGREP_CONFIG_PATH $HOME/.config/ripgrep/config

# SSH environment file
set -gx SSH_ENV $HOME/.ssh/environment

# pi: route shell, file and edit work through pi's own tools under the cursor provider.
# Cursor's native host tools bypass the guardrail hooks and pi-sandbox entirely.
set -gx PI_CURSOR_EXPOSE_BUILTIN_TOOLS 1

# set custom collation rule - sort dotfiles first, followed by uppercase and lowercase filenames
set -gx LC_COLLATE C

# zoxide configuration
set -gx _ZO_ECHO 1

# franciscolourenco/done config
set -g __done_min_cmd_duration 10000
set -g __done_exclude '^(nano|less|more|man|ssh|claude|lazygit|lazydocker|btop|htop|dive|spf|fish|bash)'

# Television
source $HOME/.config/television/shell/integration.fish

for mode in default insert
    bind --mode $mode alt-c tv_change_dir
    # Override the upstream Ctrl-R history widget to use substring (exact) matching
    bind --mode $mode ctrl-r tv_history
end

# pnpm
set -gx PNPM_HOME "$HOME/Library/pnpm"
if not string match -q -- $PNPM_HOME $PATH
    set -gx PATH "$PNPM_HOME" $PATH
end
# pnpm end

# The next line updates PATH for the Google Cloud SDK.
if [ -f '/opt/homebrew/share/google-cloud-sdk/path.fish.inc' ]
    . '/opt/homebrew/share/google-cloud-sdk/path.fish.inc'
end
