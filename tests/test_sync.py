"""Tests for the sync_downloads background task."""
from unittest.mock import patch

import pytest

from app.models import Book, Download
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
