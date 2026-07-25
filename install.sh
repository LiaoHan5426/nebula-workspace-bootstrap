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
  git clone --filter=blob:none --no-checkout "$repository" "$workspace_root"
fi

git -C "$workspace_root" sparse-checkout init --no-cone
git -C "$workspace_root" sparse-checkout set --no-cone \
  .gitignore README.md architecture docs repos.manifest.json workspace.ps1 workspace.sh
git -C "$workspace_root" checkout

tool_root="$workspace_root/.bootstrap"
if [[ -f "$tool_root/.git/HEAD" ]]; then
  git -C "$tool_root" pull --ff-only
else
  git clone "$repository" "$tool_root"
fi

"$workspace_root/workspace.sh" init "$workspace_root"
