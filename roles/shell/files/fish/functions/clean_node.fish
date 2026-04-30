function clean_node
  echo '⏰ Deleting node_modules ...'
  find node_modules --type dir --no-ignore --absolute-path --prune | while read dir
    echo "📦 Removing: $dir";
    rm -rf "$dir"
  end

  echo "📦 Removing npm cache ..."
  npm cache clean --force
  bun pm cache rm --all

  echo "📦 Removing lock files ..."
  rm -rf package-lock.json
  rm -rf yarn.lock
  rm -rf pnpm-lock.yaml
  rm -rf bun.lock

  echo "✨ Cleanup complete!"
end
