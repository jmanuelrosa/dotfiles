function create_gitconfig --description "Create a per-company .gitconfig under ~/developer/<company>"
  _ui title "🔧 New per-company git identity"

  read -P "  Company name: " company_name
  read -P "  Git user name: " user_name
  read -P "  Git email: " user_email

  if test -z "$company_name" -o -z "$user_name" -o -z "$user_email"
    _ui err "All three answers are required; nothing was written."
    return 1
  end

  set -l company_dir ~/developer/$company_name
  set -l gitconfig_file "$company_dir/.gitconfig.$company_name"

  if not mkdir -p "$company_dir"
    _ui err "Cannot create "(_ui path "$company_dir")"."
    return 1
  end

  printf '[user]\n    name = %s\n    email = %s\n' "$user_name" "$user_email" > "$gitconfig_file"
  or begin
    _ui err "Could not write "(_ui path "$gitconfig_file")"."
    return 1
  end

  _ui done "Wrote "(_ui path "$gitconfig_file")
  _ui note "Point your ~/.gitconfig at it with an includeIf gitdir directive."
end
