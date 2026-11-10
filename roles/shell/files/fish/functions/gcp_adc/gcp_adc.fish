function gcp_adc --description 'Select or create ADC for a named Google Cloud configuration'
    if contains -- "$argv[1]" -h --help; or test (count $argv) -eq 0
        echo "Usage: gcp_adc path|login [CONFIGURATION]"
        echo "Defaults to CLOUDSDK_ACTIVE_CONFIG_NAME. Login only changes this profile's ADC."
        return 0
    end

    set -l configuration "$argv[2]"
    test -n "$configuration"; or set configuration "$CLOUDSDK_ACTIVE_CONFIG_NAME"

    if not string match -qr '^[a-z][a-z0-9-]*$' -- "$configuration"
        _ui err "Specify a named Google Cloud configuration, for example: gcp_adc login didomi"
        return 1
    end

    set -l directory "$HOME/.config/gcloud-profiles/adc/$configuration"
    set -l credentials "$directory/application_default_credentials.json"

    switch "$argv[1]"
        case path
            echo "$credentials"
        case login
            set -lx CLOUDSDK_ACTIVE_CONFIG_NAME "$configuration"
            set -l account (gcloud config get-value account)
            or return 1
            if test -z "$account"
                _ui err "No account is signed in to '$configuration'. Run: gcloud auth login --configuration=$configuration"
                return 1
            end
            set -l project (gcloud config get-value project)
            or return 1
            set -l flags
            test -n "$project"; and set -a flags --project=$project

            mkdir -p "$directory"; or return 1
            chmod 700 "$directory"; or return 1

            set -lx CLOUDSDK_CONFIG "$directory"
            set -lx CLOUDSDK_ACTIVE_CONFIG_NAME default
            set -lx GOOGLE_APPLICATION_CREDENTIALS
            _ui step "Signing ADC in as $account for $configuration"
            gcloud auth application-default login "$account" $flags
            or return 1
            chmod 600 "$credentials"; or return 1
            _ui ok "ADC saved for $configuration"
        case '*'
            _ui err "Usage: gcp_adc path|login [CONFIGURATION]"
            return 1
    end
end
