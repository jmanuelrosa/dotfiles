if not status is-interactive
  return
end

set -U fish_greeting

starship init fish | source
fzf --fish | source
zoxide init fish | source
fnm env --use-on-cd | source

fish_add_path $HOME/.local/bin
fish_add_path $HOME/.yarn/bin
fish_add_path $HOME/.node/bin
fish_add_path $HOME/.bun/bin
fish_add_path $HOME/.claude

# brew specific paths
fish_add_path /opt/homebrew/sbin
fish_add_path /opt/homebrew/bin

# PSQL specific path
fish_add_path /opt/homebrew/opt/libpq/bin

# Set a global env var with the current OS
set -l CURRENT_OS (uname)

# Make default programs
# set -gx XDG_CURRENT_DESKTOP sway
set -gx BROWSER /usr/bin/google-chrome-stable
set -gx EDITOR "zed --wait"
set -gx FILE nnn
set -gx PAGER "bat --plain"
set -gx TERMINAL ghostty
set -gx VISUAL zed

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

set -gx XDG_CURRENT_DESKTOP sway

if test "$CURRENT_OS" = "Linux"
  and status is-login
  and test -z "$DISPLAY"
  and test "$XDG_VTNR" = "1"
  and test (tty) = "/dev/tty1"
  and pgrep sway > /dev/null
    sway
end

# FZF options
set -gx FD_DEFAULT_COMMAND 'fd --hidden --follow'
set -gx FZF_DEFAULT_COMMAND "$FD_DEFAULT_COMMAND --exclude .git --exclude node_modules"
set -gx FZF_DEFAULT_OPTS '
  --bind \'ctrl-t:transform:if not string match -q "Files*" $FZF_PROMPT; echo "change-prompt(Files> )+reload:fd --type f --color always"; else; echo "change-prompt(Directories> )+reload:fd --type d --color always"; end\'
  --height 50%
  --layout=reverse
  --border
  --info=inline
  --marker="*"
  --bind "?:toggle-preview"
  --bind "alt-down:half-page-down"
  --bind "alt-up:half-page-up"
  --bind "ctrl-a:toggle-all"
  --bind "ctrl-d:preview-half-page-down"
  --bind "ctrl-u:preview-half-page-up"
  --bind "ctrl-y:execute(echo {+} | pbcopy)"
  --bind \'ctrl-r:transform:if not string match -q "Hidden*" $FZF_PROMPT; echo "change-prompt(Hidden files> )+reload:fd --type f --hidden --follow --no-ignore --color always"; else; echo "change-prompt(Files&Directories> )+reload:fd --hidden --follow --color always --exclude .git --exclude node_modules --exclude .venv"; end\'
'
set fzf_history_opts --sort --exact --history-size=30000
set fzf_fd_opts --hidden --follow --exclude=.git
set fzf_preview_dir_cmd eza -T -la --git --group-directories-first --icons --color=always
set fzf_directory_opts --prompt "Files&Directories> " --bind "ctrl-o:execute($EDITOR {+} &> /dev/tty)"

fzf_configure_bindings --git_status=\e\cs --git_log=\e\cl --directory=\cp --history=\e\cr --processes=\e\cp --variables=\e\ce

# pnpm
set -gx PNPM_HOME "/Users/jmanuelrosa/Library/pnpm"
if not string match -q -- $PNPM_HOME $PATH
  set -gx PATH "$PNPM_HOME" $PATH
end
# pnpm end

# The next line updates PATH for the Google Cloud SDK.
if [ -f '/opt/homebrew/share/google-cloud-sdk/path.fish.inc' ]; . '/opt/homebrew/share/google-cloud-sdk/path.fish.inc'; end
