function tv_history --description "Search fish history with tv using substring (exact) matching"
    set -l current_prompt (commandline -cp)

    # move to the next line so the prompt is not overwritten
    printf "\n"

    set -l output (tv fish-history --input "$current_prompt" --inline --no-status-bar --exact)

    if test -n "$output"
        commandline -r "$output"
    end
    # move the cursor back up to the original prompt line
    printf "\033[A"
    commandline -f repaint
end
