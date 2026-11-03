function prt --description "Tracked PRs: ls (default), add, rm, take, watch, events"
    set -l script ~/.claude/skills/pr-track/scripts/track.py
    if not test -f $script
        _ui err "pr-track is not installed. Run: kura sync"
        return 1
    end
    if test (count $argv) -eq 0
        set argv ls
    end
    python3 $script $argv
end
