"""Config file module: read/write /data/config.json for user-configurable settings."""

import json
import os

CONFIG_FILE_PATH = "/data/config.json"

DEFAULTS = {
    "JACKETT_URL": "http://localhost:9117",
    "JACKETT_API_KEY": "",
    "JACKETT_INDEXER": "all",
    "JACKETT_CATEGORIES": "3030",
    "QBITTORRENT_URL": "http://localhost:8080",
    "QBITTORRENT_USERNAME": "admin",
    "QBITTORRENT_PASSWORD": "",
    "QBITTORRENT_SAVE_PATH": "",
    "AUDIOBOOKS_PATH": "",
    "NAMING_FORMAT": "{author}/{title}",
}


def get_config_path(app) -> str:
    """Return the path to the config file (from Flask config or default)."""
    return app.config.get("CONFIG_FILE", CONFIG_FILE_PATH)


def load_config(app) -> dict:
    """Load and return config from the JSON file. Missing keys fall back to DEFAULTS."""
    path = get_config_path(app)
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    result = dict(DEFAULTS)
    result.update({k: v for k, v in data.items() if k in DEFAULTS})
    return result


def save_config(app, updates: dict) -> None:
    """Merge updates into the config file."""
    path = get_config_path(app)
    current = load_config(app)
    current.update({k: v for k, v in updates.items() if k in DEFAULTS})
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(current, f, indent=2)


def get_setting(app, key: str) -> str:
    """Get a single setting value."""
    return load_config(app).get(key, DEFAULTS.get(key, ""))
