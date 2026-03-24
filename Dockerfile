# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

# Keeps Python from generating .pyc files and enables stdout/stderr logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create the directory used for the SQLite database volume and downloads
RUN mkdir -p /data /downloads

# Run as a non-root user for security
RUN adduser --disabled-password --gecos "" audiobookarr \
    && chown -R audiobookarr:audiobookarr /app /data /downloads

USER audiobookarr

# Default database path – mount /data as a named volume to persist between restarts
ENV DATABASE_URL=sqlite:////data/audiobookarr.db

EXPOSE 5000

# Use Gunicorn as the production WSGI server.
# Workers can be tuned via GUNICORN_WORKERS (defaults to 2).
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:5000 --workers ${GUNICORN_WORKERS:-2} run:app"]
