function _clean_claude_excludes --description "Directory names whose .claude belongs to a dependency, a cache or a build, not to you"
  # A .claude found under any of these is vendored, generated or app-owned, so no
  # clean_claude mode ever touches it. Every name here has to mean "someone else's
  # code" unambiguously, because a false hit is an unrecoverable rm -rf of your
  # settings and history. `packages` and `apps` were once on this list and are not
  # anymore: in a monorepo they are first-party source far more often than they are
  # vendored sub-projects, so excluding them hid real projects behind a message that
  # said nothing was found. `deps`, `dependencies` and `submodules` stay, since those
  # names still mean imported code. Add your own permanently via
  # CLEAN_CLAUDE_EXCLUDES, or per run with --exclude; --include drops one.
  set -l names \
    node_modules bower_components vendor vendors third_party third-party \
    deps dependencies submodules Pods Carthage DerivedData \
    .bun .npm .yarn .pnpm-store .pub-cache .cargo .rustup .m2 .gradle .swiftpm \
    .venv venv site-packages .tox .stack-work .terraform .nvm .rbenv .pyenv \
    dist build .build out target .next .nuxt .turbo .svelte-kit .output \
    .expo .dart_tool .parcel-cache __pycache__ .pytest_cache .mypy_cache \
    .cache .local Library .Trash .git

  set -a names $CLEAN_CLAUDE_EXCLUDES $argv
  printf '%s\n' $names
end
