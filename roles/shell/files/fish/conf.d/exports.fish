set -gx BROWSER /usr/bin/google-chrome-stable
set -gx EDITOR code

# switching to a software cursor instead of a hardware one,
# cursor sometimes disappears without this
set -x WLR_NO_HARDWARE_CURSORS 1
