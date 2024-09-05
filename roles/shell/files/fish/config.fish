starship init fish | source
fnm env --use-on-cd | source

fish_add_path /opt/homebrew/opt/libpq/bin

fish_add_path $HOME/.yarn/bin
fish_add_path $HOME/.node/bin
fish_add_path $HOME/.local/bin

# brew specific paths
fish_add_path /opt/homebrew/sbin
fish_add_path /opt/homebrew/bin

set -gx XDG_CURRENT_DESKTOP sway

set -gx BROWSER /usr/bin/google-chrome-stable

if status is-login
  if test -z "$DISPLAY" -a $XDG_VTNR = 1 -a (tty) = /dev/tty1 -a "(pgrep sway)"
    sway
  end
end
