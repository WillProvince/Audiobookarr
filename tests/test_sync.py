"""Tests for the sync_downloads background task."""
import logging
from unittest.mock import patch

import pytest

from app.models import Book, Download, Setting
from app import db
from app.services.sync import sync_downloads


def _make_book_and_download(app, status="queued"):
    """Helper: insert a Book + Download into the test DB and return both."""
    with app.app_context():
        book = Book(title="Dune", author="Frank Herbert", status="downloading")
        db.session.add(book)
        db.session.flush()
        download = Download(
            book_id=book.id,
            torrent_title="Dune Frank Herbert",
            magnet_or_url="magnet:?xt=urn:btih:abc123",
            indexer="TestIndexer",
            status=status,
        )
        db.session.add(download)
        db.session.commit()
        return book.id, download.id


# ---------------------------------------------------------------------------
# Completed torrent → "downloaded"
# ---------------------------------------------------------------------------


def test_sync_completed(app):
    """pausedUP state → Download becomes completed, Book becomes downloaded."""
    book_id, download_id = _make_book_and_download(app)

    fake_torrent = {"name": "Dune Frank Herbert", "state": "pausedUP"}

    with patch(
        "app.services.sync.QBittorrentClient.get_torrents",
        return_value=[fake_torrent],
    ), patch("app.services.sync.QBittorrentClient.logout"):
        sync_downloads(app)

    with app.app_context():
        dl = db.session.get(Download, download_id)
        bk = db.session.get(Book, book_id)
        assert dl.status == "completed"
        assert bk.status == "downloaded"


# ---------------------------------------------------------------------------
# Error torrent → "missing"
# ---------------------------------------------------------------------------


def test_sync_error(app):
    """error state → Download becomes error, Book becomes missing."""
    book_id, download_id = _make_book_and_download(app)

    fake_torrent = {"name": "Dune Frank Herbert", "state": "error"}

    with patch(
        "app.services.sync.QBittorrentClient.get_torrents",
        return_value=[fake_torrent],
    ), patch("app.services.sync.QBittorrentClient.logout"):
        sync_downloads(app)

    with app.app_context():
        dl = db.session.get(Download, download_id)
        bk = db.session.get(Book, book_id)
        assert dl.status == "error"
        assert bk.status == "missing"


# ---------------------------------------------------------------------------
# No active downloads → early return (no qBittorrent calls)
# ---------------------------------------------------------------------------


def test_sync_no_active_downloads(app):
    """When all downloads are completed/error, sync_downloads exits early."""
    with app.app_context():
        book = Book(title="Foundation", author="Isaac Asimov", status="downloaded")
        db.session.add(book)
        db.session.flush()
        download = Download(
            book_id=book.id,
            torrent_title="Foundation Isaac Asimov",
            magnet_or_url="magnet:?xt=urn:btih:def456",
            indexer="TestIndexer",
            status="completed",
        )
        db.session.add(download)
        db.session.commit()

    with patch(
        "app.services.sync.QBittorrentClient.get_torrents"
    ) as mock_get:
        sync_downloads(app)
        mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# qBittorrent connection failure → no exception raised
# ---------------------------------------------------------------------------


def test_sync_qbittorrent_connection_failure(app):
    """A qBittorrent connection error must not propagate out of sync_downloads."""
    _make_book_and_download(app)

    with patch(
        "app.services.sync.QBittorrentClient.get_torrents",
        side_effect=Exception("Connection refused"),
    ), patch("app.services.sync.QBittorrentClient.logout"):
        # Must not raise
        sync_downloads(app)


# ---------------------------------------------------------------------------
# _run_import called on completion
# ---------------------------------------------------------------------------


def test_sync_completed_calls_run_import(app):
    """When a torrent transitions to completed, _run_import should be invoked."""
    book_id, download_id = _make_book_and_download(app)

    fake_torrent = {
        "name": "Dune Frank Herbert",
        "state": "pausedUP",
        "content_path": "/downloads/Dune Frank Herbert",
    }

    with patch(
        "app.services.sync.QBittorrentClient.get_torrents",
        return_value=[fake_torrent],
    ), patch("app.services.sync.QBittorrentClient.logout"), \
       patch("app.services.sync._run_import") as mock_run_import:
        sync_downloads(app)

    mock_run_import.assert_called_once()


def test_sync_run_import_skipped_when_audiobooks_path_not_set(app):
    """_run_import should skip the file move when AUDIOBOOKS_PATH is not configured."""
    book_id, download_id = _make_book_and_download(app)

    fake_torrent = {
        "name": "Dune Frank Herbert",
        "state": "pausedUP",
        "content_path": "/downloads/Dune Frank Herbert",
    }

    # Ensure AUDIOBOOKS_PATH is empty in the DB
    with app.app_context():
        Setting.set("AUDIOBOOKS_PATH", "")

    with patch(
        "app.services.sync.QBittorrentClient.get_torrents",
        return_value=[fake_torrent],
    ), patch("app.services.sync.QBittorrentClient.logout"), \
       patch("app.services.importer.import_download") as mock_import:
        sync_downloads(app)

    mock_import.assert_not_called()


def test_sync_stores_content_path(app):
    """content_path from qBittorrent should be stored on download.download_path."""
    book_id, download_id = _make_book_and_download(app)

    fake_torrent = {
        "name": "Dune Frank Herbert",
        "state": "pausedUP",
        "content_path": "/downloads/Dune Frank Herbert",
    }

    with patch(
        "app.services.sync.QBittorrentClient.get_torrents",
        return_value=[fake_torrent],
    ), patch("app.services.sync.QBittorrentClient.logout"), \
       patch("app.services.sync._run_import"):
        sync_downloads(app)

    with app.app_context():
        dl = db.session.get(Download, download_id)
        assert dl.download_path == "/downloads/Dune Frank Herbert"


# ---------------------------------------------------------------------------
# qBittorrent 5.x stoppedUP → completed
# ---------------------------------------------------------------------------


def test_sync_stopped_up_completed(app):
    """stoppedUP state (qBittorrent 5.x) → Download becomes completed, Book becomes downloaded."""
    book_id, download_id = _make_book_and_download(app)

    fake_torrent = {"name": "Dune Frank Herbert", "state": "stoppedUP"}

    with patch(
        "app.services.sync.QBittorrentClient.get_torrents",
        return_value=[fake_torrent],
    ), patch("app.services.sync.QBittorrentClient.logout"), \
       patch("app.services.sync._run_import"):
        sync_downloads(app)

    with app.app_context():
        dl = db.session.get(Download, download_id)
        bk = db.session.get(Book, book_id)
        assert dl.status == "completed"
        assert bk.status == "downloaded"


# ---------------------------------------------------------------------------
# Unmapped qBittorrent state → warning logged, no update
# ---------------------------------------------------------------------------


def test_sync_unmapped_state_logs_warning(app, caplog):
    """An unmapped qBittorrent state should log a WARNING and leave the download unchanged."""
    book_id, download_id = _make_book_and_download(app, status="queued")

    fake_torrent = {"name": "Dune Frank Herbert", "state": "checkingResumeData"}

    with patch(
        "app.services.sync.QBittorrentClient.get_torrents",
        return_value=[fake_torrent],
    ), patch("app.services.sync.QBittorrentClient.logout"), \
       caplog.at_level(logging.WARNING, logger="app.services.sync"):
        sync_downloads(app)

    assert any("checkingResumeData" in r.message for r in caplog.records), (
        "Expected a WARNING containing the unmapped state name"
    )

    with app.app_context():
        dl = db.session.get(Download, download_id)
        assert dl.status == "queued"


# ---------------------------------------------------------------------------
# Punctuation/whitespace mismatch between DB title and qBittorrent name
# ---------------------------------------------------------------------------


def test_sync_normalize_punctuation_mismatch(app):
    """DB title with stripped punctuation must match qBittorrent name with original punctuation."""
    with app.app_context():
        book = Book(
            title="Heir of Fire",
            author="Sarah J Maas",
            status="downloading",
        )
        db.session.add(book)
        db.session.flush()
        download = Download(
            book_id=book.id,
            torrent_title="Sarah J Maas   Throne of Glass 3   Heir of Fire",
            magnet_or_url="magnet:?xt=urn:btih:abc999",
            indexer="TestIndexer",
            status="queued",
        )
        db.session.add(download)
        db.session.commit()
        book_id = book.id
        download_id = download.id

    fake_torrent = {
        "name": "Sarah J. Maas - Throne of Glass 3 - Heir of Fire",
        "state": "stoppedUP",
    }

    with patch(
        "app.services.sync.QBittorrentClient.get_torrents",
        return_value=[fake_torrent],
    ), patch("app.services.sync.QBittorrentClient.logout"), \
       patch("app.services.sync._run_import"):
        sync_downloads(app)

    with app.app_context():
        dl = db.session.get(Download, download_id)
        bk = db.session.get(Book, book_id)
        assert dl.status == "completed"
        assert bk.status == "downloaded"


# ---------------------------------------------------------------------------
# Real qBittorrent torrent name used as torrent_name for import_download
# ---------------------------------------------------------------------------


def test_sync_run_import_uses_real_torrent_name(app):
    """_run_import must pass the real qBittorrent torrent name to import_download."""
    with app.app_context():
        book = Book(
            title="Heir of Fire",
            author="Sarah J Maas",
            status="downloading",
        )
        db.session.add(book)
        db.session.flush()
        download = Download(
            book_id=book.id,
            # Jackett-stripped title stored in the DB (punctuation removed)
            torrent_title="Sarah J Maas   Throne of Glass 3   Heir of Fire",
            magnet_or_url="magnet:?xt=urn:btih:abc999",
            indexer="TestIndexer",
            status="queued",
        )
        db.session.add(download)
        db.session.commit()
        # Ensure AUDIOBOOKS_PATH is set so _run_import doesn't skip
        Setting.set("AUDIOBOOKS_PATH", "/audiobooks")

    real_torrent_name = "Sarah J. Maas - Throne of Glass 3 - Heir of Fire"
    fake_torrent = {
        "name": real_torrent_name,
        "state": "stoppedUP",
        "content_path": f"/downloads/tmp/{real_torrent_name}",
    }

    with patch(
        "app.services.sync.QBittorrentClient.get_torrents",
        return_value=[fake_torrent],
    ), patch(
        "app.services.sync.QBittorrentClient.logout"
    ), patch(
        "app.services.importer.import_download", return_value=None
    ) as mock_import:
        sync_downloads(app)

    mock_import.assert_called_once()
    # The real qBittorrent torrent name must be used, not the Jackett-stripped DB title
    assert mock_import.call_args.kwargs["torrent_name"] == real_torrent_name
