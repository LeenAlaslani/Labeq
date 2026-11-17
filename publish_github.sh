#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
git rev-parse --is-inside-work-tree >/dev/null
remote=$(git remote get-url origin)
case "$remote" in
  https://github.com/LeenAlaslani/Labeq|https://github.com/LeenAlaslani/Labeq.git|git@github.com:LeenAlaslani/Labeq.git) ;;
  *) echo "Use the existing LeenAlaslani/Labeq origin." >&2; exit 2 ;;
esac
branch=$(git symbolic-ref --short HEAD)
if [[ "$branch" == main ]]; then
  echo "Publish an implementation branch and use a pull request into main." >&2
  exit 2
fi
git push -u origin "$branch"
