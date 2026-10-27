function spf --description "superfile, changing the shell to its last directory on quit"
    # superfile cannot change its parent shell's directory, so with cd_on_quit it writes a
    # `cd` command to this file and leaves sourcing it to the shell.
    set -l last_dir "$HOME/Library/Application Support/superfile/lastdir"

    command spf $argv

    if test -f "$last_dir"
        source "$last_dir"
        command rm -f -- "$last_dir"
    end
end
