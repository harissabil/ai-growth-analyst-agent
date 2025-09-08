FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Work in /app
WORKDIR /app

# Install deps first
COPY pyproject.toml uv.lock* ./
# If you use requirements.txt instead, copy it and use the commented RUN below
RUN uv sync --frozen --no-cache

# Copy the rest of the app into /app
COPY . .

# Start the app
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
