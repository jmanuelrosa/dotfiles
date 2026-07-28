function _clean_claude_excludes --description "Directory names whose .claude belongs to a dependency, a cache or a build, not to you"
  # A .claude found under any of these is vendored, generated or app-owned, so no
  # clean_claude mode ever touches it. Workspace-shaped names (packages, apps, deps)
  # are in the list too: opt one back in per run with --include, or add your own
  # permanently via CLEAN_CLAUDE_EXCLUDES.
  set -l names \
    node_modules bower_components vendor vendors third_party third-party \
    packages apps deps dependencies submodules Pods Carthage DerivedData \
    .bun .npm .yarn .pnpm-store .pub-cache .cargo .rustup .m2 .gradle .swiftpm \
    .venv venv site-packages .tox .stack-work .terraform .nvm .rbenv .pyenv \
    dist build .build out target .next .nuxt .turbo .svelte-kit .output \
    .expo .dart_tool .parcel-cache __pycache__ .pytest_cache .mypy_cache \
    .cache .local Library .Trash .git

  set -a names $CLEAN_CLAUDE_EXCLUDES $argv
  printf '%s\n' $names
end
