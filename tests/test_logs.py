"""Tests for the logs routes and RingBufferHandler."""
import json
import logging

import pytest

from app.logging_setup import RingBufferHandler


# ---------------------------------------------------------------------------
# RingBufferHandler unit tests
# ---------------------------------------------------------------------------

def test_ring_buffer_capacity():
    """Oldest records are dropped when the buffer is full."""
    handler = RingBufferHandler(capacity=5)
    for i in range(7):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=f"message {i}",
            args=(),
            exc_info=None,
        )
        handler.emit(record)
    records = handler.get_records()
    assert len(records) == 5
    # Only the last 5 messages should remain
    messages = [r.getMessage() for r in records]
    assert "message 0" not in messages
    assert "message 1" not in messages
    assert "message 6" in messages


def test_ring_buffer_level_filter():
    """get_records respects min_level filter."""
    handler = RingBufferHandler(capacity=100)
    for level in (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR):
        record = logging.LogRecord(
            name="test",
            level=level,
            pathname="",
            lineno=0,
            msg=f"level {level}",
            args=(),
            exc_info=None,
        )
        handler.emit(record)

    assert len(handler.get_records(min_level=logging.DEBUG)) == 4
    assert len(handler.get_records(min_level=logging.INFO)) == 3
    assert len(handler.get_records(min_level=logging.WARNING)) == 2
    assert len(handler.get_records(min_level=logging.ERROR)) == 1


def test_ring_buffer_clear():
    """clear() empties the buffer."""
    handler = RingBufferHandler(capacity=10)
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="hello", args=(), exc_info=None,
    )
    handler.emit(record)
    assert len(handler.get_records()) == 1
    handler.clear()
    assert len(handler.get_records()) == 0


# ---------------------------------------------------------------------------
# Logs routes integration tests
# ---------------------------------------------------------------------------

def test_logs_page_returns_200(client):
    resp = client.get("/logs")
    assert resp.status_code == 200
    assert b"Logs" in resp.data


def test_api_logs_returns_json_structure(client):
    resp = client.get("/api/logs")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "entries" in data
    assert "total" in data
    assert isinstance(data["entries"], list)
    assert isinstance(data["total"], int)


def test_api_logs_level_filter_error(client, app):
    """?level=error only returns ERROR+ records."""
    from app.logging_setup import ring_handler

    ring_handler.clear()

    info_rec = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="info message", args=(), exc_info=None,
    )
    error_rec = logging.LogRecord(
        name="test", level=logging.ERROR, pathname="", lineno=0,
        msg="error message", args=(), exc_info=None,
    )
    ring_handler.emit(info_rec)
    ring_handler.emit(error_rec)

    resp = client.get("/api/logs?level=error")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert all(e["level"] in ("ERROR", "CRITICAL") for e in data["entries"])
    assert any(e["message"] == "error message" for e in data["entries"])
    assert all(e["message"] != "info message" for e in data["entries"])

    ring_handler.clear()


def test_api_logs_default_returns_all_levels(client, app):
    """Default (no level param) returns DEBUG and above."""
    from app.logging_setup import ring_handler

    ring_handler.clear()

    debug_rec = logging.LogRecord(
        name="test", level=logging.DEBUG, pathname="", lineno=0,
        msg="debug message", args=(), exc_info=None,
    )
    ring_handler.emit(debug_rec)

    resp = client.get("/api/logs")
    data = json.loads(resp.data)
    assert any(e["message"] == "debug message" for e in data["entries"])

    ring_handler.clear()
