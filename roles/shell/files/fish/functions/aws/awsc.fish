function awsc --description 'Show the active AWS profile and the identity it resolves to'
    if not set -q AWS_PROFILE
        _ui warn "No AWS_PROFILE set. Pick one with awsp."
        return 1
    end

    set -l identity (aws sts get-caller-identity --query '[Account, Arn]' --output text 2>/dev/null)
    or begin
        _ui err "Credentials for '$AWS_PROFILE' are missing or expired. Sign in with awsl."
        return 1
    end

    set -l fields (string split \t -- "$identity")
    _ui ok "$AWS_PROFILE"
    _ui note "account $fields[1]"
    _ui note "$fields[2]"
end
