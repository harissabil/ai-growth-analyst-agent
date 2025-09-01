#!/usr/bin/env bash
set -Eeuo pipefail

# ---- log everything to LogFiles/startup.log ----
mkdir -p /home/LogFiles
exec > >(tee -a /home/LogFiles/startup.log) 2>&1

echo "[startup] PWD=$(pwd)"
echo "[startup] Listing /home/site/wwwroot:"
ls -la /home/site/wwwroot || true

APP_ROOT="/home/site/wwwroot"
VENV="$APP_ROOT/.venv"

echo "[startup] Python: $(python3 --version || python --version || true)"
echo "[startup] WHICH python: $(which python3 || which python || true)"
echo "[startup] PORT env: ${PORT:-<unset>}"
echo "[startup] WEBSITES_PORT: ${WEBSITES_PORT:-<unset>}"

# ---- ensure venv ----
if [ ! -d "$VENV" ]; then
  echo "[startup] creating venv at $VENV"
  python3 -m venv "$VENV" || python -m venv "$VENV"
fi
# shellcheck disable=SC1090
source "$VENV/bin/activate"
python -V
pip --version

# ---- install uv ----
python -m pip install --upgrade pip
pip install --no-cache-dir uv

# ---- sync deps (prefer lock) ----
if [ -f "$APP_ROOT/uv.lock" ]; then
  echo "[startup] uv sync --frozen --no-dev"
  uv sync --frozen --no-dev
else
  echo "[startup] uv sync --no-dev (no lock file)"
  uv sync --no-dev
fi

# ---- preflight import: fail fast with traceback if settings/env are missing ----
echo "[startup] preflight import app.main ..."
python - <<'PY'
import traceback, sys
print(">>> importing app.main for preflight ...")
try:
    import app.main  # noqa
    print(">>> import OK")
except Exception as e:
    print(">>> import FAILED:", e)
    traceback.print_exc()
    sys.exit(1)
PY

# ---- run gunicorn/uvicorn ----
export PYTHONPATH="$APP_ROOT"
BIND_PORT="${PORT:-${WEBSITES_PORT:-8000}}"
echo "[startup] starting gunicorn on 0.0.0.0:${BIND_PORT}"
exec gunicorn -k uvicorn.workers.UvicornWorker \
  -w "${WORKERS:-1}" -b "0.0.0.0:${BIND_PORT}" app.main:app
