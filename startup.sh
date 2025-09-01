# startup.sh
#!/usr/bin/env bash
set -euo pipefail

# ----- Paths -----
APP_ROOT="/home/site/wwwroot"
VENV="$APP_ROOT/.venv"

echo "[startup] Python: $(python3 --version || python --version || true)"

# ----- Ensure venv -----
if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV" || python -m venv "$VENV"
fi
# shellcheck disable=SC1090
source "$VENV/bin/activate"

# ----- Install uv (fast!) -----
python -m pip install --upgrade pip
pip install --no-cache-dir uv

# ----- Sync project deps with uv.lock / pyproject.toml -----
# (uses system site inside the venv)
uv sync --frozen --no-dev || uv sync --no-dev

# ----- Run the app -----
# Azure provides $PORT
export PYTHONPATH="$APP_ROOT"
exec gunicorn -k uvicorn.workers.UvicornWorker \
  -w ${WORKERS:-2} -b 0.0.0.0:${PORT:-8000} app.main:app
