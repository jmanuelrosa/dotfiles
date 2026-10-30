# npm_token

Wrappers that hand the npm registry tokens to a single package-manager call instead of to every process.

```fish
npm install
npx some-cli
pnpm install --frozen-lockfile
pnpx some-cli
bun install
bunx some-cli
yarn install
```

`~/.npmrc` (from the `apps` role) expands `${NPM_TOKEN}` for registry.npmjs.org and, on the work profile, `${DID_NPM_TOKEN}` for the Didomi GitLab package registry.
npm, pnpm, bun and yarn v1 all read that file, and so do the `npx`, `pnpx` and `bunx` runners, so each of those seven is wrapped and a token has to be in the environment of the package manager and nowhere else.

Each role that owns a token stores it in the login keychain from the vault through the shared [keychain_token.yml](../../../../tasks/keychain_token.yml), and appends one `VAR:service:account` entry to the fish list `NPM_TOKEN_KEYCHAIN_ITEMS` from its `conf.d` file:

| Variable | Role | Keychain names | `conf.d` file |
|---|---|---|---|
| `NPM_TOKEN` | `shell` | `NPM_TOKEN_KEYCHAIN` | `secrets.fish` |
| `DID_NPM_TOKEN` | `work` | `DID_NPM_TOKEN_KEYCHAIN` | `work-secrets.fish` |

`_npm_token` reads every listed item with `security find-generic-password -w` and sets it as a function-scoped export, so only the wrapped command and its children see it.
The parent shell never does.
The seven wrappers call it with `--publish-only`, so they do this only for a publishing subcommand of `npm`, `pnpm`, `bun` or `yarn`: `publish`, `unpublish`, `deprecate`, `dist-tag`, `owner`, `access`, `team`, `token` or `whoami`.
Every other wrapped call runs with no token and no keychain lookup.
Calling `_npm_token` directly always hands the tokens over, which is how a private-scope install gets one: `_npm_token npm ci`, `_npm_token yarn install --immutable`.
An empty vault value leaves its entry out of the list and deletes the keychain item.

An entry may carry a fourth field, a directory: `VAR:service:account:dir`.
It applies only when `$PWD` is that directory or below it, and it is applied after every unscoped entry, so it wins for the same variable.
The work role uses this to hand the Didomi token over as `NPM_TOKEN` under `DID_NPM_TOKEN_AS_NPM_TOKEN_UNDER`, because Didomi repos name `${NPM_TOKEN}` in their own `.npmrc` and `.yarnrc.yml`.

yarn v1 aborts with `Failed to replace env in config` on any unset `${VAR}` in `.npmrc`, so for `yarn` every listed variable that is still unset is exported empty.
npm and yarn 2+ tolerate an unset one.

When an entry is listed but the keychain has no item under it, the wrapper warns on stderr and still runs the command without that variable.
npm then sends the literal `${NAME}` placeholder, so public packages keep installing and only that registry rejects the request.
Re-running the playbook on the profile that owns the item restores it: `make run` for `NPM_TOKEN`, `make run PROFILE=work` for `DID_NPM_TOKEN`.
The playbook stops with a named error rather than writing blind when the keychain itself cannot be read, which is the case over SSH until `security unlock-keychain`.

Only a fish function call goes through these wrappers.
A bash script, a Makefile recipe, a git hook or an IDE that runs `npm` directly gets no token; run it from fish as `_npm_token <command> ...` when it needs one.
Wrapped installs run without the token, so a dependency's lifecycle scripts never see it, and `npx`, `pnpx` and `bunx` never get one because they execute the package they fetch.
The cost is that a private-scope install needs the explicit `_npm_token` prefix: without it, public packages keep installing and the private ones are rejected by the registry.
A publish-type call costs one `security` lookup per listed item. Every other call costs none.
A fish session that was open when a vault value was emptied keeps the old entry until it restarts, and warns about the deleted item until then.
