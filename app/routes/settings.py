"""Routes for application settings."""

from flask import Blueprint, current_app, jsonify, render_template, request

from app.config_file import DEFAULTS, load_config, save_config
from app.services.jackett import search_torrents
from app.services.qbittorrent import QBittorrentClient, QBittorrentError

settings_bp = Blueprint("settings", __name__)

SETTING_KEYS = list(DEFAULTS.keys())


@settings_bp.route("/settings")
def settings_page():
    current_settings = load_config(current_app._get_current_object())
    # Show placeholder for secrets instead of the real value
    display = dict(current_settings)
    if display.get("JACKETT_API_KEY"):
        display["JACKETT_API_KEY"] = "********"
    if display.get("QBITTORRENT_PASSWORD"):
        display["QBITTORRENT_PASSWORD"] = "********"
    return render_template("settings.html", settings=display)


@settings_bp.route("/api/settings", methods=["GET"])
def api_get_settings():
    result = load_config(current_app._get_current_object())
    if result.get("JACKETT_API_KEY"):
        result["JACKETT_API_KEY"] = "********"
    if result.get("QBITTORRENT_PASSWORD"):
        result["QBITTORRENT_PASSWORD"] = "********"
    return jsonify(result)


@settings_bp.route("/api/settings", methods=["POST"])
def api_save_settings():
    payload = request.get_json(silent=True) or {}
    updates = {}
    for key in SETTING_KEYS:
        if key in payload:
            value = payload[key]
            if value not in ("********",):
                updates[key] = value
    save_config(current_app._get_current_object(), updates)
    return jsonify({"saved": True})


@settings_bp.route("/api/settings/test/jackett", methods=["POST"])
def api_test_jackett():
    """Test Jackett connectivity."""
    app = current_app._get_current_object()
    cfg = load_config(app)
    payload = request.get_json(silent=True) or {}
    url = payload.get("JACKETT_URL") or cfg.get("JACKETT_URL", "")
    api_key = payload.get("JACKETT_API_KEY") or cfg.get("JACKETT_API_KEY", "")
    indexer = payload.get("JACKETT_INDEXER") or cfg.get("JACKETT_INDEXER", "all")
    categories = payload.get("JACKETT_CATEGORIES") or cfg.get("JACKETT_CATEGORIES", "3030")

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
    app = current_app._get_current_object()
    cfg = load_config(app)
    payload = request.get_json(silent=True) or {}
    url = payload.get("QBITTORRENT_URL") or cfg.get("QBITTORRENT_URL", "")
    username = payload.get("QBITTORRENT_USERNAME") or cfg.get("QBITTORRENT_USERNAME", "")
    password = payload.get("QBITTORRENT_PASSWORD") or ""
    if password in ("********", ""):
        password = cfg.get("QBITTORRENT_PASSWORD", "")

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
