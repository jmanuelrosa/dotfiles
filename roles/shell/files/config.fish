starship init fish | source

set -gx BROWSER /usr/bin/google-chrome-stable

if status is-login
  if test -z "$DISPLAY" -a $XDG_VTNR = 1 -a (tty) = /dev/tty1 -a "(pgrep sway)"
    sway
  end
end