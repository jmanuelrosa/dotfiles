function _npm_token --description "Run a publishing package manager command with the configured registry tokens read from the login keychain for this call only"
    set -l program $argv[1]
    set -l subcommand
    for arg in $argv[2..-1]
        if not string match -q -- '-*' $arg
            set subcommand $arg
            break
        end
    end
    if not contains -- $program npm pnpm bun yarn; or not contains -- "$subcommand" publish unpublish deprecate dist-tag owner access team token whoami
        command $argv
        return
    end

    for item in $NPM_TOKEN_KEYCHAIN_ITEMS
        set -l fields (string split -m 2 : -- $item)
        set -l token (security find-generic-password -s $fields[2] -a $fields[3] -w 2>/dev/null)
        if test $status -ne 0; or test -z "$token"
            _ui warn "No '$fields[2]' item in the login keychain, running $argv[1] without $fields[1]" >&2
            _ui note "restore it by re-running the playbook on the profile that owns $fields[1] (make run, or make run PROFILE=work)" >&2
            continue
        end
        set -fx $fields[1] $token
    end

    command $argv
end
