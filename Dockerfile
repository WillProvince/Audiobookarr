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

# Install gosu for privilege dropping in the entrypoint
RUN apt-get update && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

# Create the directory used for the SQLite database volume and downloads
RUN mkdir -p /data /downloads /audiobooks

# Create a non-root user; the entrypoint remaps its uid/gid at runtime via
# PUID/PGID and then drops privileges with gosu.
RUN adduser --disabled-password --gecos "" audiobookarr \
    && chown -R audiobookarr:audiobookarr /app /data /downloads /audiobooks

# Copy and enable the entrypoint that handles PUID/PGID remapping
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Default database path – mount /data as a named volume to persist between restarts
ENV DATABASE_URL=sqlite:////data/audiobookarr.db

EXPOSE 5000

ENTRYPOINT ["/entrypoint.sh"]

# Use Gunicorn as the production WSGI server.
# Default to 1 worker: APScheduler uses a background *thread*, not a process.
# Gunicorn forks workers after app creation, which kills the scheduler thread in
# child processes.  A single worker avoids this fork-safety issue while still
# handling the async sync work correctly.  Set GUNICORN_WORKERS > 1 only if you
# know what you are doing (e.g. you have moved the scheduler out of the app).
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:5000 --workers ${GUNICORN_WORKERS:-1} run:app"]
