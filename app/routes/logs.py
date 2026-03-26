import datetime
import logging

from flask import Blueprint, jsonify, render_template, request

from app.logging_setup import ring_handler

logs_bp = Blueprint("logs", __name__)

_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


@logs_bp.route("/logs")
def logs_page():
    return render_template("logs.html")


@logs_bp.route("/api/logs")
def api_logs():
    """
    Return buffered log records as JSON.
    Query params:
        level  – min level name: debug | info | warning | error  (default: debug)
        limit  – max records to return, newest-first             (default: 500)
    """
    level_name = request.args.get("level", "debug").lower()
    min_level = _LEVEL_MAP.get(level_name, logging.DEBUG)
    try:
        limit = int(request.args.get("limit", 500))
    except ValueError:
        limit = 500

    records = ring_handler.get_records(min_level=min_level)
    # newest first, capped at limit
    records = records[-limit:][::-1]

    entries = [
        {
            "time": _fmt_time(r),
            "level": r.levelname,
            "logger": r.name,
            "message": r.getMessage(),
        }
        for r in records
    ]
    return jsonify({"entries": entries, "total": len(ring_handler.get_records())})


def _fmt_time(record: logging.LogRecord) -> str:
    dt = datetime.datetime.fromtimestamp(record.created)
    return dt.strftime("%Y-%m-%d %H:%M:%S")
