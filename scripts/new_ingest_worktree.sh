#!/bin/zsh
set -euo pipefail

if (( $# < 1 || $# > 3 )); then
  echo "usage: $0 <ZOTERO_KEY> [vault-repo] [base-branch]" >&2
  exit 2
fi

key="${1:u}"
vault="${2:-${RESEARCH_VAULT_ROOT:-$PWD}}"
base="${3:-main}"
branch="ingest/${key}"
dest="$(dirname "$vault")/rv-${key}"

if [[ ! "$key" =~ '^[A-Z0-9]{8}$' ]]; then
  echo "invalid Zotero key: $key" >&2
  exit 2
fi

cd "$vault"
git rev-parse --is-inside-work-tree >/dev/null
git worktree add "$dest" -b "$branch" "$base"
cat <<MSG
Created: $dest
Branch:  $branch

In the new terminal:
  export RESEARCH_VAULT_ROOT="$dest"
  cd "$dest"
MSG
