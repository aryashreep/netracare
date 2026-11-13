FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# uv for fast, lockfile-based installs.
RUN pip install --no-cache-dir uv

# Install deps first for layer caching. pyproject.toml is created by /speckit-implement.
COPY pyproject.toml* uv.lock* ./
RUN if [ -f pyproject.toml ]; then uv sync --frozen || uv sync; fi

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
