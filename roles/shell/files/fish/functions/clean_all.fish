function clean_all
  echo '🧹 Cleaning Homebrew ...'
  brew autoremove
  brew cleanup --prune=all --scrub

  echo '🧹 Cleaning system (mole) ...'
  mo clean
  mo optimize

  echo '🧹 Cleaning Node artifacts (cwd) ...'
  clean_node

  echo '✨ All cleanup complete!'
end
