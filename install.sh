#!/usr/bin/env bash
set -euo pipefail

workspace_root="${1:-$PWD/nebula-workspace}"
repository="${NEBULA_WORKSPACE_REPOSITORY:-https://github.com/LiaoHan5426/nebula-workspace-bootstrap.git}"

if [[ -f "$workspace_root/.git/HEAD" ]]; then
  echo "Using existing workspace repository: $workspace_root"
elif [[ -d "$workspace_root" ]] && [[ -n "$(ls -A "$workspace_root")" ]]; then
  echo "Refusing to overwrite non-empty directory '$workspace_root'. Migrate or back it up first." >&2
  exit 1
else
  git clone "$repository" "$workspace_root"
fi

"$workspace_root/workspace.sh" init "$workspace_root"
