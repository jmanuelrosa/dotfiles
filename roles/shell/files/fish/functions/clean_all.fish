function clean_all
  echo '🧹 Cleaning Homebrew ...'
  clean:brew

  echo '🧹 Cleaning system (mole) ...'
  clean:system

  echo '🧹 Cleaning Node artifacts (cwd) ...'
  clean:node

  echo '✨ All cleanup complete!'
end
