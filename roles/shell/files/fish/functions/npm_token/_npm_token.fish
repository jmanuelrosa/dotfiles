function _npm_token --description "Run a package manager command with the configured registry tokens read from the login keychain for this call only"
    set -l publish_only false
    if test "$argv[1]" = --publish-only
        set publish_only true
        set -e argv[1]
    end

    set -l program $argv[1]
    set -l subcommand
    for arg in $argv[2..-1]
        if not string match -q -- '-*' $arg
            set subcommand $arg
            break
        end
    end

    set -l inject true
    if test $publish_only = true
        if not contains -- $program npm pnpm bun yarn; or not contains -- "$subcommand" publish unpublish deprecate dist-tag owner access team token whoami
            set inject false
        end
    end

    if test $inject = true
        set -l unscoped
        set -l scoped
        for item in $NPM_TOKEN_KEYCHAIN_ITEMS
            set -l fields (string split -m 3 : -- $item)
            if test -z "$fields[4]"
                set -a unscoped $item
            else if test "$PWD" = "$fields[4]"; or string match -q -- "$fields[4]/*" "$PWD"
                set -a scoped $item
            end
        end

        for item in $unscoped $scoped
            set -l fields (string split -m 3 : -- $item)
            set -l token (security find-generic-password -s $fields[2] -a $fields[3] -w 2>/dev/null)
            if test $status -ne 0; or test -z "$token"
                _ui warn "No '$fields[2]' item in the login keychain, running $argv[1] without $fields[1]" >&2
                _ui note "restore it by re-running the playbook on the profile that owns $fields[1] (make run, or make run PROFILE=work)" >&2
                continue
            end
            set -fx $fields[1] $token
        end
    end

    # yarn v1 aborts on any unset ${VAR} in .npmrc, where npm and yarn 2+ tolerate it.
    if test $program = yarn
        for item in $NPM_TOKEN_KEYCHAIN_ITEMS
            set -l variable (string split -m 1 : -- $item)[1]
            set -q $variable; or set -fx $variable ""
        end
    end

    command $argv
end
