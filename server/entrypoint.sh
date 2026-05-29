#!/bin/sh
# Finger server entrypoint
# 1. Sweep expired plans from disk
# 2. Start uvicorn

set -e

PLANS_DIR="${FINGER_PLANS_DIR:-/data/plans}"

# Startup sweep: remove any expired plan files
if [ -d "$PLANS_DIR" ]; then
    now=$(date +%s)
    find "$PLANS_DIR" -name '*.meta' | while read -r meta; do
        expires=$(python3 -c "
import json, sys
try:
    data = json.load(open('$meta'))
    ts = data.get('expires_at')
    print(ts if ts else 'null')
except Exception:
    print('null')
" 2>/dev/null || echo "null")
        if [ "$expires" != "null" ] && [ "$now" -gt "$expires" ] 2>/dev/null; then
            plan="${meta%.meta}.md"
            rm -f "$meta" "$plan"
        fi
    done
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
