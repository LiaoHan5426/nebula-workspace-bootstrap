#!/usr/bin/env bash
set -euo pipefail

command_name="${1:-init}"
workspace_root="${2:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
tool_root="$workspace_root"
if [[ ! -f "$tool_root/bootstrap.py" ]]; then
  cache_home="${XDG_CACHE_HOME:-$HOME/.cache}"
  tool_root="$cache_home/nebula-workspace-bootstrap"
fi

if [[ "$command_name" == "doctor" ]]; then
  echo "Workspace: $workspace_root"
  test -f "$workspace_root/.git/HEAD" && echo "Meta repository: OK" || {
    echo "Meta repository: MISSING OR INVALID"
    exit 1
  }
  for repo in nebula nebula-studio; do
    test -d "$workspace_root/$repo/.git" && echo "$repo: OK" || echo "$repo: MISSING"
  done
  test -d "$workspace_root/.knowledge/agent-memory/.git" && echo "agent-memory: OK" || echo "agent-memory: MISSING"
  test -x "$workspace_root/.venv/bin/code-review-graph" && echo "code-review-graph: OK" || echo "code-review-graph: MISSING"
  exit 0
fi

if [[ ! -f "$workspace_root/.git/HEAD" ]]; then
  echo "'$workspace_root' is not a valid workspace Git repository." >&2
  echo "Clone https://github.com/LiaoHan5426/nebula-workspace-bootstrap.git as the workspace root first." >&2
  exit 1
fi

if [[ "$command_name" == "update" ]]; then
  git -C "$workspace_root" pull --ff-only
  if [[ "$tool_root" != "$workspace_root" ]]; then
    git -C "$tool_root" pull --ff-only
  fi
elif [[ "$command_name" != "init" ]]; then
  echo "Usage: $0 [init|update|doctor] [workspace-root]" >&2
  exit 2
fi

python3 "$tool_root/bootstrap.py" \
  --workspace-root "$workspace_root" \
  --manifest "$workspace_root/repos.manifest.json" \
  --repos all \
  --yes
