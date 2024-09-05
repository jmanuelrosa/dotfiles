starship init fish | source
fnm env --use-on-cd | source

fish_add_path /opt/homebrew/opt/libpq/bin

fish_add_path $HOME/.yarn/bin
fish_add_path $HOME/.node/bin
fish_add_path $HOME/.local/bin

# brew specific paths
fish_add_path /opt/homebrew/sbin
fish_add_path /opt/homebrew/bin

# Kitty config
set -gx KITTY_LISTEN_ON "unix:/tmp/kitty-$KITTY_PID"

# Make default programs
set -gx BROWSER /usr/bin/google-chrome-stable
set -gx EDITOR "zed --wait"
set -gx FILE nnn
set -gx PAGER "bat --plain"
set -gx TERMINAL kitty
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

if status is-login
  if test -z "$DISPLAY" -a $XDG_VTNR = 1 -a (tty) = /dev/tty1 -a "(pgrep sway)"
    sway
  end
end
