function awsl --description 'Sign in to the SSO session behind the active AWS profile'
    if not set -q AWS_PROFILE
        _ui err "No AWS_PROFILE set. Pick one with awsp, which also signs in."
        return 1
    end

    aws sso login; or return 1
    awsc
end
