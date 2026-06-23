#!/usr/bin/env bash
set -euo pipefail
rtk_path="$DIR/rtk"
if [[ ! -f "$rtk_path" ]]; then
    rtk_path=$(command -v rtk 2>/dev/null || true)
fi
if [[ -n "$rtk_path" ]]; then
    export PATH="$DIR:$PATH"
fi
echo '{"message":"ok","passed":true}'