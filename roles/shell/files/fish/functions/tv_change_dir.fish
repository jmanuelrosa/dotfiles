function tv_change_dir --description "Pick a directory with tv and cd into it"
    set -l result (tv dirs --inline --no-status-bar)
    if test -n "$result"
        cd "$result"
        commandline -f repaint
    end
end
