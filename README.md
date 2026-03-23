# Audiobookarr
Automated audiobook collection management tool. Similar to Radarr or Sonarr but for audiobooks and written in Python.

---

## Features
- Search for audiobooks via the [Open Library](https://openlibrary.org/) API
- Discover torrents automatically using [Jackett](https://github.com/Jackett/Jackett)
- Queue downloads directly to [qBittorrent](https://www.qbittorrent.org/)
- Dark-themed web UI accessible from any browser
- Persistent library with wanted / downloading / downloaded status tracking

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

Open `.env` and set at least a strong `SECRET_KEY`. The other values can be
updated later from the Settings page once the stack is running.

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

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

---

## Environment Variables

All settings have sensible defaults and can also be changed from the
**Settings** page inside the app.

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `change-me-in-production` | Flask session secret — **change this** |
| `DATABASE_URL` | `sqlite:////data/audiobookarr.db` (Docker) | SQLAlchemy database URI |
| `JACKETT_URL` | `http://localhost:9117` | Jackett base URL |
| `JACKETT_API_KEY` | *(empty)* | Jackett API key |
| `JACKETT_INDEXER` | `all` | Jackett indexer slug |
| `JACKETT_CATEGORIES` | `3030` | Newznab category IDs (3030 = AudioBook) |
| `QBITTORRENT_URL` | `http://localhost:8080` | qBittorrent Web UI URL |
| `QBITTORRENT_USERNAME` | `admin` | qBittorrent username |
| `QBITTORRENT_PASSWORD` | `adminadmin` | qBittorrent password |
| `QBITTORRENT_SAVE_PATH` | *(empty)* | Download save path inside the container |
| `GUNICORN_WORKERS` | `2` | Number of Gunicorn worker processes |
| `FLASK_DEBUG` | `0` | Set to `1` for debug mode (dev only) |

