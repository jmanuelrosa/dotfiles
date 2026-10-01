function pi_last_error --description "Print the most recent pi-cursor-sdk failure captured by pi_debug"
    set -l debug_dir "$HOME/.pi/agent/cursor-sdk-debug"
    set -l latest (find "$debug_dir/sessions" -name errors.jsonl -type f 2>/dev/null | xargs -I{} stat -f '%m %N' {} 2>/dev/null | sort -rn | head -n 1 | cut -d' ' -f2-)

    if test -z "$latest"
        _ui warn "No captured pi-cursor-sdk errors under "(_ui path "$debug_dir")
        _ui note "Launch pi via pi_debug to capture failure detail next time"
        return 1
    end

    _ui title "🔎 Last pi-cursor-sdk error"
    _ui item (_ui path "$latest")
    _ui blank
    tail -n 1 "$latest" | jq -r '"\(.error.label): \(.error.message)\n\(.error.stack // "no stack")"'
end
