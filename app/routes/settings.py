"""Routes for application settings."""

from flask import Blueprint, current_app, jsonify, render_template, request

from app import db
from app.models import Setting
from app.services.jackett import search_torrents
from app.services.qbittorrent import QBittorrentClient, QBittorrentError

settings_bp = Blueprint("settings", __name__)

SETTING_KEYS = [
    "JACKETT_URL",
    "JACKETT_API_KEY",
    "JACKETT_INDEXER",
    "JACKETT_CATEGORIES",
    "QBITTORRENT_URL",
    "QBITTORRENT_USERNAME",
    "QBITTORRENT_PASSWORD",
    "QBITTORRENT_SAVE_PATH",
]


@settings_bp.route("/settings")
def settings_page():
    current_settings = {
        key: Setting.get(key, current_app.config.get(key, ""))
        for key in SETTING_KEYS
    }
    return render_template("settings.html", settings=current_settings)


@settings_bp.route("/api/settings", methods=["GET"])
def api_get_settings():
    result = {
        key: Setting.get(key, current_app.config.get(key, ""))
        for key in SETTING_KEYS
    }
    # Mask the password
    if result.get("QBITTORRENT_PASSWORD"):
        result["QBITTORRENT_PASSWORD"] = "********"
    if result.get("JACKETT_API_KEY"):
        result["JACKETT_API_KEY"] = "********"
    return jsonify(result)


@settings_bp.route("/api/settings", methods=["POST"])
def api_save_settings():
    payload = request.get_json(silent=True) or {}
    for key in SETTING_KEYS:
        if key in payload:
            value = payload[key]
            # Skip masked placeholder values
            if value not in ("********",):
                Setting.set(key, value)
    return jsonify({"saved": True})


@settings_bp.route("/api/settings/test/jackett", methods=["POST"])
def api_test_jackett():
    """Test Jackett connectivity."""
    payload = request.get_json(silent=True) or {}
    url = payload.get("JACKETT_URL") or Setting.get("JACKETT_URL", current_app.config.get("JACKETT_URL", ""))
    api_key = payload.get("JACKETT_API_KEY") or Setting.get("JACKETT_API_KEY", current_app.config.get("JACKETT_API_KEY", ""))
    indexer = payload.get("JACKETT_INDEXER") or Setting.get("JACKETT_INDEXER", current_app.config.get("JACKETT_INDEXER", "all"))
    categories = payload.get("JACKETT_CATEGORIES") or Setting.get("JACKETT_CATEGORIES", current_app.config.get("JACKETT_CATEGORIES", "3030"))

    if not url or not api_key:
        return jsonify({"ok": False, "error": "URL and API key are required"}), 400

    try:
        results = search_torrents(base_url=url, api_key=api_key, query="test", indexer=indexer, categories=categories, timeout=10)
        return jsonify({"ok": True, "results_count": len(results)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


@settings_bp.route("/api/settings/test/qbittorrent", methods=["POST"])
def api_test_qbittorrent():
    """Test qBittorrent connectivity."""
    payload = request.get_json(silent=True) or {}
    url = payload.get("QBITTORRENT_URL") or Setting.get("QBITTORRENT_URL", current_app.config.get("QBITTORRENT_URL", ""))
    username = payload.get("QBITTORRENT_USERNAME") or Setting.get("QBITTORRENT_USERNAME", current_app.config.get("QBITTORRENT_USERNAME", ""))
    password = payload.get("QBITTORRENT_PASSWORD") or ""
    if password in ("********", ""):
        password = Setting.get("QBITTORRENT_PASSWORD", current_app.config.get("QBITTORRENT_PASSWORD", ""))

    if not url:
        return jsonify({"ok": False, "error": "URL is required"}), 400

    client = QBittorrentClient(url, username, password)
    try:
        client.login()
        client.logout()
        return jsonify({"ok": True})
    except QBittorrentError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502
