if not status is-interactive
  return
end

set -U fish_greeting

starship init fish | source
zoxide init fish | source
fnm env --use-on-cd | source
source $HOME/.config/television/shell/integration.fish

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
set -gx FILE nnn
set -gx PAGER "bat --plain"
set -gx TERMINAL ghostty
set -gx VISUAL zed
set -gx RIPGREP_CONFIG_PATH "$HOME/.config/ripgrep/config"

# nnn settings
set -gx NNN_FIFO /tmp/nnn.fifo # breaks NnnExplorer feature
set -gx NNN_SSHFS_OPTS sshfs -o follow_symlinks
set -gx NNN_USE_EDITOR 1
set -gx NNN_COLORS 2136
set -gx NNN_TRASH 2 # configure gio trash
set -gx NNN_FCOLORS 030304020000060801030500 # filetype colors. this mimics dircolors
# d: detail mode
# e: open text files in terminal
# u: use selection, don't prompt to choose between selection and hovered entry
# U: show file's owner and group in status bar
set -gx NNN_OPTS deuU
set -gx NNN_PLUG "c:fzcd;d:diffs;h:fzhist;k:pskill;m:nmount;o:fzopen;p:fzplug;p:preview-tui;j:autojump;"
set -gx NNN_BMS "d:$HOME/downloads/"
set -gx NNN_BATSTYLE "changes,numbers"
set -gx NNN_BATTHEME base16

# ripgrep options
set -gx RIPGREP_CONFIG_PATH $HOME/.config/ripgrep/config

# SSH environment file
set -gx SSH_ENV $HOME/.ssh/environment

# set custom collation rule - sort dotfiles first, followed by uppercase and lowercase filenames
set -gx LC_COLLATE C

# zoxide configuration
set -gx _ZO_ECHO 1

# franciscolourenco/done config
set -g __done_min_cmd_duration 10000
set -g __done_exclude '^(nano|less|more|man|ssh|claude|lazygit|btop|htop|ctop|nnn|fish|bash)'

# pnpm
set -gx PNPM_HOME "$HOME/Library/pnpm"
if not string match -q -- $PNPM_HOME $PATH
  set -gx PATH "$PNPM_HOME" $PATH
end
# pnpm end

# The next line updates PATH for the Google Cloud SDK.
if [ -f '/opt/homebrew/share/google-cloud-sdk/path.fish.inc' ]; . '/opt/homebrew/share/google-cloud-sdk/path.fish.inc'; end
