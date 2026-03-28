# Audiobookarr
Automated audiobook collection management tool. Similar to Radarr or Sonarr but for audiobooks and written in Python.

---

## Features
- Search for audiobooks via the [Open Library](https://openlibrary.org/) API
- Discover torrents automatically using [Jackett](https://github.com/Jackett/Jackett)
- Queue downloads directly to [qBittorrent](https://www.qbittorrent.org/)
- Dark-themed web UI accessible from any browser
- Persistent library with wanted / downloading / downloaded status tracking
- In-browser log viewer at `/logs` with level filtering, auto-refresh, and one-click copy

---

## 🐳 Docker Quick Start (recommended)

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed

### 1. Clone & configure

```bash
git clone https://github.com/WillProvince/Audiobookarr.git
cd Audiobookarr
cp .env.example .env
```

Open `.env` and set at least:
- A strong `SECRET_KEY`.
- `PUID` and `PGID` to match your host user (run `id` on the host — the values
  next to `uid=` and `gid=` are what you want).  This ensures the container can
  write to the `/audiobooks` and `/downloads` bind mounts without permission
  errors.

### 2. Start the stack

```bash
docker compose up -d
```

This starts three services:

| Service | URL | Notes |
|---------|-----|-------|
| **Audiobookarr** | <http://localhost:5000> | Main web UI |
| **Jackett** | <http://localhost:9117> | Torrent indexer proxy |
| **qBittorrent** | <http://localhost:8080> | Download client (default: admin / adminadmin) |

### 3. Connect Jackett & qBittorrent

1. Open Jackett (<http://localhost:9117>) and copy the **API Key** shown at the top.
2. Open the Audiobookarr **Settings** page (<http://localhost:5000/settings>).
3. Paste the API key and click **Test Jackett** — you should see *✓ Connected*.
4. If you changed the qBittorrent password, update it in Settings and click **Test qBittorrent**.
5. Click **Save Settings**.

### 4. Add indexers to Jackett

In the Jackett UI click **+ Add Indexer** and search for audiobook-friendly
trackers (e.g. AudioBookBay). Audiobookarr will search them all automatically.

### Useful commands

```bash
# View logs
docker compose logs -f audiobookarr

# Stop everything
docker compose down

# Stop and remove persistent data (⚠ deletes your library)
docker compose down -v

# Rebuild after a code change
docker compose up -d --build
```

---

## Manual / Development Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                  # starts the Flask dev server on http://localhost:5000
```

Set `FLASK_DEBUG=1` to enable the interactive debugger (development only).

---

## Logs

The **Logs** page at [`/logs`](http://localhost:5000/logs) gives you a
live view of everything the application has logged since startup:

- **Level filter** — switch between ALL, INFO+, WARNING+, and ERROR+ to focus
  on what matters.
- **Auto-refresh** — the page polls `/api/logs` every 10 seconds automatically
  (toggle the checkbox to disable).
- **Refresh button** — fetch the latest records immediately without reloading
  the page.
- **Copy all** — copies every visible log line to the clipboard in the format
  `2026-03-26 12:34:56 [INFO] app.services.sync: message`.

Log records are stored in an in-memory ring buffer (last 2,000 entries) — no
log files are written to disk. Docker logs (`docker compose logs -f`) still
show all output as before.

---

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

---

## Environment Variables

Only infrastructure-level settings are configured via environment variables.
All other settings (Jackett, qBittorrent, library paths, naming format) are
configured via the **Settings page** in the web UI and stored in
`/data/config.json` on the persisted Docker volume.

| Variable | Default | Description |
|----------|---------|-------------|
| `PUID` | `1000` | UID to run as inside the container — set to your host user's UID (`id -u`) to fix volume permissions |
| `PGID` | `1000` | GID to run as inside the container — set to your host user's GID (`id -g`) to fix volume permissions |
| `SECRET_KEY` | `change-me-in-production` | Flask session secret — **change this** |
| `DATABASE_URL` | `sqlite:////data/audiobookarr.db` (Docker) | SQLAlchemy database URI |

