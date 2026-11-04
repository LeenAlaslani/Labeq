#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
REMOTE="${1:-}"
if [[ ! "$REMOTE" =~ ^https://github\.com/[^/]+/[^/]+\.git$ ]]; then
  echo 'Usage: bash publish_github.sh https://github.com/YOUR_USERNAME/labeq.git'
  exit 2
fi
if [ -d .git ]; then
  echo 'This directory is already a Git repo. Inspect git status; not overwriting anything.'
  exit 1
fi
if [ -f .env ] || [ -f .local_api_key ]; then
  echo 'Private .env or .local_api_key detected. Remove them from this publishing copy before continuing.'
  exit 1
fi
git init -b main
git add .
if git diff --cached --name-only | grep -E '(^|/)(\.env|\.local_api_key)$|\.safetensors$|LoRA.*\.zip$'; then
  echo 'ERROR: a private config or model weight is staged! Stop.'
  exit 1
fi
git commit -m 'Initial public LABEQ portfolio release'
git remote add origin "$REMOTE"
git push -u origin main
printf 'Published source. Enable Pages in GitHub Settings > Pages > main > /docs.\n'
