function clean_all --description "Run every cleaner in turn: Homebrew, system caches, Node artifacts"
  _ui title "🍺 Cleaning Homebrew ..."
  clean:brew

  _ui title "🖥️  Cleaning system (mole) ..."
  clean:system

  _ui title "📦 Cleaning Node artifacts (cwd) ..."
  clean:node

  _ui done "All cleanup complete!"
end
