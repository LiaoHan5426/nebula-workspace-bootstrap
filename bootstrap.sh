#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOTSTRAP_PY="$SCRIPT_DIR/bootstrap.py"

if [[ ! -f "$BOOTSTRAP_PY" ]]; then
  echo "bootstrap.py not found at $BOOTSTRAP_PY" >&2
  exit 1
fi

WORKSPACE_ROOT=""
REPOS="all"
EDITOR="all"
SKIP_PULL=0
SKIP_GRAPH_BUILD=0
SKIP_RTK=0
FORCE_RTK=0
FORCE_AGENTS=0
FORCE=0
YES=0
MANIFEST=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace-root)
      WORKSPACE_ROOT="$2"
      shift 2
      ;;
    --repos)
      REPOS="$2"
      shift 2
      ;;
    --editor)
      EDITOR="$2"
      shift 2
      ;;
    --skip-pull)
      SKIP_PULL=1
      shift 1
      ;;
    --skip-graph-build)
      SKIP_GRAPH_BUILD=1
      shift 1
      ;;
    --skip-rtk)
      SKIP_RTK=1
      shift 1
      ;;
    --force-rtk)
      FORCE_RTK=1
      shift 1
      ;;
    --force-agents)
      FORCE_AGENTS=1
      shift 1
      ;;
    --force)
      FORCE=1
      shift 1
      ;;
    -y|--yes)
      YES=1
      shift 1
      ;;
    --manifest)
      MANIFEST="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$WORKSPACE_ROOT" ]]; then
  echo "--workspace-root is required" >&2
  exit 1
fi

ARGS=( "--workspace-root" "$WORKSPACE_ROOT" "--repos" "$REPOS" "--editor" "$EDITOR" )
[[ "$SKIP_PULL" -eq 1 ]] && ARGS+=( "--skip-pull" )
[[ "$SKIP_GRAPH_BUILD" -eq 1 ]] && ARGS+=( "--skip-graph-build" )
[[ "$SKIP_RTK" -eq 1 ]] && ARGS+=( "--skip-rtk" )
[[ "$FORCE_RTK" -eq 1 ]] && ARGS+=( "--force-rtk" )
[[ "$FORCE_AGENTS" -eq 1 ]] && ARGS+=( "--force-agents" )
[[ "$FORCE" -eq 1 ]] && ARGS+=( "--force" )
[[ "$YES" -eq 1 ]] && ARGS+=( "--yes" )
[[ -n "$MANIFEST" ]] && ARGS+=( "--manifest" "$MANIFEST" )

echo "[bootstrap.sh] python $BOOTSTRAP_PY ${ARGS[*]}"
python "$BOOTSTRAP_PY" "${ARGS[@]}"