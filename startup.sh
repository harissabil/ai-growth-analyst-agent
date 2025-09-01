#!/usr/bin/env bash
set -Eeuo pipefail

# ---- log to /home/LogFiles/startup.log ----
mkdir -p /home/LogFiles
exec > >(tee -a /home/LogFiles/startup.log) 2>&1

APP_ROOT="/home/site/wwwroot"

echo "[startup] PWD=$(pwd)"
echo "[startup] Listing /home/site/wwwroot:"
ls -la /home/site/wwwroot || true

# Use the interpreter Azure gives us (antenv)
PY_BIN="$(which python3 || which python)"
echo "[startup] Python: $($PY_BIN --version 2>&1)"
echo "[startup] PY_BIN=$PY_BIN"
echo "[startup] PORT=${PORT:-<unset>}  WEBSITES_PORT=${WEBSITES_PORT:-<unset>}"

# Upgrade pip and install uv into the current env (antenv)
$PY_BIN -m pip install --upgrade pip
$PY_BIN -m pip install --no-cache-dir uv

# ---- Install project deps ----
# Prefer uv.lock; fallback to requirements.txt; fallback to pyproject
if [ -f "$APP_ROOT/uv.lock" ]; then
  echo "[startup] uv pip install from uv.lock"
  # Install resolved wheels recorded in lock using uv's pip subcommand
  uv pip install -r <(uv export --locked)
elif [ -f "$APP_ROOT/requirements.txt" ]; then
  echo "[startup] uv pip install -r requirements.txt"
  uv pip install -r "$APP_ROOT/requirements.txt"
else
  echo "[startup] uv pip install -e . (pyproject only)"
  uv pip install -e "$APP_ROOT"
fi

# ---- Preflight import to surface config/env errors clearly ----
echo "[startup] preflight import app.main ..."
$PY_BIN - <<'PY'
import traceback, sys
print(">>> importing app.main for preflight ...")
try:
    import app.main  # noqa: F401
    print(">>> import OK")
except Exception as e:
    print(">>> import FAILED:", e)
    traceback.print_exc()
    sys.exit(1)
PY

# ---- Launch gunicorn/uvicorn ----
export PYTHONPATH="$APP_ROOT"
BIND_PORT="${PORT:-${WEBSITES_PORT:-8000}}"
echo "[startup] starting gunicorn on 0.0.0.0:${BIND_PORT}"
exec gunicorn -k uvicorn.workers.UvicornWorker \
  -w "${WORKERS:-1}" -b "0.0.0.0:${BIND_PORT}" app.main:app
