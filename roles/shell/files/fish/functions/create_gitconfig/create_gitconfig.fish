function create_gitconfig --description "Create ~/Developer/work/.gitconfig.<company>, the identity ~/.gitconfig includes for ~/Developer/work/<company>"
    _ui title "🔧 New per-company git identity"

    read -P "  Company name: " company_name
    read -P "  Git user name: " user_name
    read -P "  Git email: " user_email

    if test -z "$company_name" -o -z "$user_name" -o -z "$user_email"
        _ui err "All three answers are required; nothing was written."
        return 1
    end

    set -l work_dir ~/Developer/work
    set -l gitconfig_file "$work_dir/.gitconfig.$company_name"

    if not mkdir -p "$work_dir"
        _ui err "Cannot create "(_ui path "$work_dir")"."
        return 1
    end

    printf '[user]\n    name = %s\n    email = %s\n' "$user_name" "$user_email" >"$gitconfig_file"
    or begin
        _ui err "Could not write "(_ui path "$gitconfig_file")"."
        return 1
    end

    _ui done "Wrote "(_ui path "$gitconfig_file")
    _ui note "Add an includeIf for gitdir/i:$work_dir/$company_name to ~/.gitconfig if it has none yet."
end
