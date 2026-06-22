#!/usr/bin/env bash
# Workspace-local RTK Cursor preToolUse hook (installed by workspace-bootstrap).
# Based on rtk-ai/rtk hooks/cursor/rtk-rewrite.sh — uses local binary, not PATH.

set -euo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RTK_BIN="$HOOK_DIR/rtk"
if [ ! -x "$RTK_BIN" ]; then
  RTK_BIN="$HOOK_DIR/rtk.exe"
fi

if ! command -v jq &>/dev/null; then
  echo "[rtk] WARNING: jq not installed; hook cannot rewrite. Install: https://jqlang.github.io/jq/download/" >&2
  echo '{}'
  exit 0
fi

if [ ! -x "$RTK_BIN" ]; then
  echo "[rtk] WARNING: RTK binary not found at $HOOK_DIR" >&2
  echo '{}'
  exit 0
fi

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$CMD" ]; then
  echo '{}'
  exit 0
fi

if echo "$CMD" | grep -Eq '^\s*rtk(\.exe)?\s+' || echo "$CMD" | grep -Eq '^\s*trk(\.exe)?\s+'; then
  echo '{}'
  exit 0
fi

REWRITTEN=$("$RTK_BIN" rewrite "$CMD" 2>/dev/null) || { echo '{}'; exit 0; }

if [ "$CMD" = "$REWRITTEN" ]; then
  echo '{}'
  exit 0
fi

jq -n --arg cmd "$REWRITTEN" '{
  "permission": "allow",
  "updated_input": { "command": $cmd }
}'
