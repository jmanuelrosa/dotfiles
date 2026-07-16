#!/usr/bin/env bash
# One-shot working-tree context for the /commit skill: branch/base, status,
# stats, filtered + capped diffs, untracked previews, recent subjects.
# Everything the drafting steps need, in a single Bash round-trip.
set -uo pipefail

FILE_CAP="${COMMIT_DIFF_FILE_CAP:-250}"
UNTRACKED_CAP="${COMMIT_UNTRACKED_CAP:-80}"

cd "$(git rev-parse --show-toplevel)" || exit 1

git() { command git -c color.ui=never "$@"; }

# Noisy paths excluded from the drafting view only; they still appear in the
# stat sections so they can be committed with the concern they belong to.
EXCLUDES=(
  ':(exclude)*package-lock.json'
  ':(exclude)*yarn.lock'
  ':(exclude)*pnpm-lock.yaml'
  ':(exclude)*bun.lock*'
  ':(exclude)*.min.js'
  ':(exclude)*.min.css'
  ':(exclude)*.map'
  ':(exclude)*node_modules/*'
  ':(exclude)*dist/*'
  ':(exclude)*build/*'
  ':(exclude)*.next/*'
  ':(exclude)*.generated.*'
  ':(exclude)*_generated.*'
  ':(exclude)*.pb.ts'
)

cap_per_file() {
  awk -v cap="$FILE_CAP" '
    /^diff --git / { n = 0; print; next }
    {
      n++
      if (n <= cap) print
      else if (n == cap + 1) print "... [capped at " cap " lines; run git diff -- <path> for the rest]"
    }
  '
}

echo "== branch =="
BASE=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
if [ -z "$BASE" ] && git remote get-url origin >/dev/null 2>&1; then
  git remote set-head origin -a >/dev/null 2>&1
  BASE=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
fi
echo "BASE=${BASE:-<none: no origin>}"
echo "BRANCH=$(git branch --show-current)"

echo
echo "== status (porcelain) =="
git status --porcelain=v1

echo
echo "== staged stat =="
git diff --cached --stat

echo
echo "== unstaged stat =="
git diff --stat

echo
echo "== staged diff (noisy paths excluded, capped per file) =="
git diff --cached -- . "${EXCLUDES[@]}" | cap_per_file

echo
echo "== unstaged diff (noisy paths excluded, capped per file) =="
git diff -- . "${EXCLUDES[@]}" | cap_per_file

echo
echo "== untracked previews (first $UNTRACKED_CAP lines each) =="
git status --porcelain=v1 | while IFS= read -r line; do
  case "$line" in
    '?? '*)
      f=${line#'?? '}
      echo "--- $f"
      if [ -f "$f" ]; then
        head -n "$UNTRACKED_CAP" -- "$f"
        total=$(wc -l < "$f" | tr -d ' ')
        [ "$total" -gt "$UNTRACKED_CAP" ] && echo "... [capped: $total lines total]"
      else
        echo "[directory or non-regular file]"
      fi
      ;;
  esac
done

echo
echo "== recent subjects =="
git log -n 10 --pretty='%h %s' 2>/dev/null || echo "<no commits yet>"
