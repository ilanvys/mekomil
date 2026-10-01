#!/usr/bin/env bash

set -u

previous_sha="${VERCEL_GIT_PREVIOUS_SHA:-}"
current_sha="${VERCEL_GIT_COMMIT_SHA:-}"

if [[ -z "$previous_sha" || -z "$current_sha" ]]; then
  echo "Build required: Git comparison refs are unavailable."
  exit 1
fi

if ! git -C .. cat-file -e "${previous_sha}^{commit}" 2>/dev/null \
  || ! git -C .. cat-file -e "${current_sha}^{commit}" 2>/dev/null; then
  echo "Build required: a Git comparison ref is unavailable."
  exit 1
fi

if git -C .. diff --quiet "$previous_sha" "$current_sha" -- mcp/; then
  echo "Build ignored: mcp/ is unchanged."
  exit 0
fi

echo "Build required: mcp/ changed."
exit 1
