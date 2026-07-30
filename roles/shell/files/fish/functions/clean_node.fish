function clean_node --description "Delete node_modules under the current tree, clear the package caches and lock files"
  _ui title "📦 Deleting node_modules ..."
  find node_modules --type dir --no-ignore --absolute-path --prune | while read dir
    _ui item (_ui path "$dir")
    rm -rf "$dir"
  end

  _ui step "Removing npm and bun caches"
  npm cache clean --force
  bun pm cache rm --all

  _ui step "Removing lock files"
  rm -rf package-lock.json
  rm -rf yarn.lock
  rm -rf pnpm-lock.yaml
  rm -rf bun.lock

  _ui done "Cleanup complete!"
end
