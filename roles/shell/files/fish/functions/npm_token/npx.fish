function npx --description "npx with the npm registry tokens from the login keychain for this call only"
    _npm_token --publish-only npx $argv
end
