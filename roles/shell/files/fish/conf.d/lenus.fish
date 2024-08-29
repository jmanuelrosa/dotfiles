alias lenus:build "lenus shared-services build && lenus shared-constants build && lenus eslint build && lenus configuration build && lenus i18n build && lenus public-frontend build && lenus public-frontend build"
alias lenus:types "pnpm --filter core run check-types"
alias lenus:lint "pnpm --filter core run lint"
alias lenus:fix "node_modules/prettier/bin/prettier.cjs --write "

alias lenus:test "pnpm --filter core run internal:run:jest --watch "

alias lenus:stripe "stripe listen --forward-to lenus.localhost:3030/api/webhooks/stripe-test"
alias lenus:charge "lenus jobs run chargeInstallments --environment local"

alias lenus:db "pgcli --port 5432 -h localhost -u postgres -d app"
alias lenus:db:reset "lenus db migrate clean; lenus db migrate latest; lenus db seed"
alias lenus:gql "lenus core save-schema; lenus core generate-gql-types"

alias lenus:reset "npx nx reset"
alias lenus:reset:hard "lenus nx c; find . -name 'ts-declarations' -exec rm -f {} +;lenus nx cc"

function lenus_prs
  clear
  gh pr list --state=open \
    --search 'author:mattsoltani author:sudo-at-night author:jmanuelrosa author:DanielRaouf author:brennofaneco' \
    --json title,author,url --template '{{range .}}{{tablerow (printf "%v" .author.name | autocolor "green") .title .url }}{{end}}'
end

function lenus_merged
  clear
  git log origin/master --pretty=format:'%C(yellow)%h %Cblue%ad %Cgreen%an%Cgreen%d %Creset%s' --date=iso --author='Matt Soltani' --author='Daniel Tadros' --author='José Manuel Rosa Moncayo' --author='Brenno Pimenta' --author='Patryk Mazur'
end

alias lenus:git:pr "lenus_prs"
alias lenus:git:merged "lenus_merged"
