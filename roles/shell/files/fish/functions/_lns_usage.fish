function _lns_usage --description "Print lns usage"
  echo "Usage: lns [ROOT] [options]"
  echo
  echo "List every symlink under ROOT (default: the current directory) with the absolute"
  echo "path it points at. Read-only unless --remove is given."
  echo
  echo "Options"
  echo "  -c, --contains STRING  only links whose target path contains STRING"
  echo "  -r, --remove           remove the listed links, after one confirmation"
  echo "  -n, --dry-run          with --remove, list what would go and remove nothing"
  echo "  -y, --yes              skip the confirmation prompt"
  echo "  -a, --all              include dependency, cache and build trees"
  echo "  -h, --help             this text"
  echo
  echo "--contains matches the target, not the link's own name, so"
  echo "'lns --contains old-repo --remove' drops every link pointing into a repo you moved."
  echo "A link is reported and never followed, so the walk cannot descend into a target."
  echo "Broken links are flagged and are removable like any other."
  echo "Dependency, cache and build trees (node_modules, .venv, dist, Library, ...) are"
  echo "skipped unless --all: recursing them means hundreds of node_modules/.bin links."
  echo "The list comes from clean_claude, so CLEAN_CLAUDE_EXCLUDES extends it here too."
end
