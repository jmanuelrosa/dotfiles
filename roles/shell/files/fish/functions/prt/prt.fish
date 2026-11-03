function prt --description "Tracked PRs: ls (default), add, rm, take, watch, events"
    set -l script ~/.config/kura/catalog/skills/pr-track/scripts/track.py
    if not test -f $script
        _ui err "pr-track is not in the agent catalog. Run: make run-role ROLE=ai"
        return 1
    end
    if test (count $argv) -eq 0
        set argv ls
    end
    python3 $script $argv
end
