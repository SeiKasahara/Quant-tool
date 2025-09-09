#!/bin/sh
set -e

REQ=/app/requirements.txt
HASHFILE=/app/.requirements_hash

if [ -f "$REQ" ]; then
  new=$(python - <<PY
import hashlib
print(hashlib.sha256(open('$REQ','rb').read()).hexdigest())
PY
)
  old=$(cat "$HASHFILE" 2>/dev/null || echo "")
  if [ "$new" != "$old" ]; then
    echo "requirements changed or first run — installing packages..."
    pip install --no-cache-dir -r "$REQ"
    echo "$new" > "$HASHFILE"
  else
    echo "requirements unchanged"
  fi
fi

# Exec the passed command (e.g. sh -c "alembic ... && uvicorn ...")
exec "$@"
