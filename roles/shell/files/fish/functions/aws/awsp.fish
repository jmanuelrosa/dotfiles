function awsp --description 'Switch AWS_PROFILE, signing in to SSO when the cached token has expired'
    if contains -- "$argv[1]" -h --help
        echo "Usage: awsp [PROFILE|off]"
        echo "Without a profile, pick one from the AWS config. off clears AWS_PROFILE."
        return 0
    end

    if test "$argv[1]" = off
        set -e AWS_PROFILE
        _ui ok "Cleared AWS_PROFILE"
        return 0
    end

    set -l profile "$argv[1]"
    if test -z "$profile"
        set profile (tv aws-profiles --inline --no-status-bar)
        test -n "$profile"; or return 0
    else if not contains -- "$profile" (aws configure list-profiles)
        _ui err "No AWS profile named '$profile'. Run awsp with no argument to pick one."
        return 1
    end

    set -gx AWS_PROFILE "$profile"
    if not aws sts get-caller-identity >/dev/null 2>&1
        _ui step "No valid SSO token for $profile, signing in"
        aws sso login; or return 1
    end
    awsc
end
