"""Routes for book search, library management, and torrent downloads."""

import logging

from flask import Blueprint, current_app, jsonify, render_template, request

from app import db
from app.models import Book, Download
from app.config_file import get_setting as _cfg
from app.services import book_search as bs
from app.services import jackett as jk
from app.services.qbittorrent import QBittorrentClient, QBittorrentError

books_bp = Blueprint("books", __name__)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


@books_bp.route("/")
def index():
    """Dashboard – show all tracked books."""
    books = Book.query.order_by(Book.added_at.desc()).all()
    return render_template("index.html", books=books)


@books_bp.route("/search")
def search_page():
    """Book search page."""
    return render_template("search.html")


# ---------------------------------------------------------------------------
# API: Book search (Open Library)
# ---------------------------------------------------------------------------


@books_bp.route("/api/search")
def api_search():
    """Search Open Library for books.

    Query params:
        q (str): search term
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing search query"}), 400

    try:
        results = bs.search_books(query)
    except Exception as exc:
        current_app.logger.error("Book search failed: %s", exc)
        return jsonify({"error": "Book search failed", "detail": str(exc)}), 502

    return jsonify(results)


# ---------------------------------------------------------------------------
# API: Library management
# ---------------------------------------------------------------------------


@books_bp.route("/api/books", methods=["GET"])
def api_list_books():
    books = Book.query.order_by(Book.added_at.desc()).all()
    return jsonify([b.to_dict() for b in books])


@books_bp.route("/api/books", methods=["POST"])
def api_add_book():
    """Add a book to the wanted list."""
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    author = (payload.get("author") or "").strip()
    open_library_id = (payload.get("open_library_id") or "").strip() or None
    cover_url = (payload.get("cover_url") or "").strip() or None

    if not title or not author:
        return jsonify({"error": "title and author are required"}), 400

    # Avoid duplicates by open_library_id when available
    if open_library_id:
        existing = Book.query.filter_by(open_library_id=open_library_id).first()
        if existing:
            return jsonify({"error": "Book already in library", "book": existing.to_dict()}), 409

    book = Book(
        title=title,
        author=author,
        open_library_id=open_library_id,
        cover_url=cover_url,
        status="wanted",
    )
    db.session.add(book)
    db.session.commit()
    return jsonify(book.to_dict()), 201


@books_bp.route("/api/books/<int:book_id>", methods=["DELETE"])
def api_delete_book(book_id):
    book = db.session.get(Book, book_id)
    if book is None:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(book)
    db.session.commit()
    return jsonify({"deleted": book_id})


# ---------------------------------------------------------------------------
# API: Torrent search via Jackett
# ---------------------------------------------------------------------------


@books_bp.route("/api/books/<int:book_id>/torrents")
def api_search_torrents(book_id):
    """Search Jackett for torrents for a specific book."""
    book = db.session.get(Book, book_id)
    if book is None:
        return jsonify({"error": "Not found"}), 404

    jackett_url = _setting("JACKETT_URL")
    api_key = _setting("JACKETT_API_KEY")
    indexer = _setting("JACKETT_INDEXER")
    categories = _setting("JACKETT_CATEGORIES")

    if not api_key:
        return jsonify({"error": "Jackett API key not configured"}), 503

    query = f"{book.title} {book.author}"
    try:
        results = jk.search_torrents(
            base_url=jackett_url,
            api_key=api_key,
            query=query,
            indexer=indexer,
            categories=categories,
        )
    except Exception as exc:
        current_app.logger.error("Jackett search failed: %s", exc)
        return jsonify({"error": "Jackett search failed", "detail": str(exc)}), 502

    return jsonify(results)


# ---------------------------------------------------------------------------
# API: Download a torrent via qBittorrent
# ---------------------------------------------------------------------------


@books_bp.route("/api/books/<int:book_id>/download", methods=["POST"])
def api_download(book_id):
    """Send a torrent to qBittorrent and record the download."""
    book = db.session.get(Book, book_id)
    if book is None:
        return jsonify({"error": "Not found"}), 404
    payload = request.get_json(silent=True) or {}

    magnet_or_url = (payload.get("magnet_or_url") or "").strip()
    torrent_title = (payload.get("title") or "").strip()
    indexer = (payload.get("indexer") or "").strip()

    logger.info(
        "api_download: book_id=%s magnet_or_url=%r torrent_title=%r indexer=%r",
        book_id, magnet_or_url, torrent_title, indexer,
    )

    if not magnet_or_url:
        return jsonify({"error": "magnet_or_url is required"}), 400

    qbt_url = _setting("QBITTORRENT_URL")
    qbt_user = _setting("QBITTORRENT_USERNAME")
    qbt_pass = _setting("QBITTORRENT_PASSWORD")
    save_path = _setting("QBITTORRENT_SAVE_PATH")

    logger.info(
        "api_download: qbt_url=%r qbt_user=%r save_path=%r",
        qbt_url, qbt_user, save_path,
    )

    client = QBittorrentClient(qbt_url, qbt_user, qbt_pass)
    try:
        client.add_torrent(magnet_or_url, save_path=save_path)
    except QBittorrentError as exc:
        current_app.logger.error("qBittorrent error: %s", exc, exc_info=True)
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        current_app.logger.error("qBittorrent unexpected error: %s", exc, exc_info=True)
        return jsonify({"error": "qBittorrent connection failed", "detail": str(exc)}), 502
    finally:
        client.logout()

    logger.info("api_download: torrent accepted by qBittorrent for book_id=%s", book_id)

    download = Download(
        book_id=book.id,
        torrent_title=torrent_title or magnet_or_url[:200],
        magnet_or_url=magnet_or_url,
        indexer=indexer,
        status="queued",
    )
    db.session.add(download)
    book.status = "downloading"
    db.session.commit()

    return jsonify(download.to_dict()), 201


@books_bp.route("/api/sync", methods=["POST"])
def api_sync():
    """Manually trigger a qBittorrent status sync."""
    from app.services.sync import sync_downloads

    try:
        sync_downloads(current_app._get_current_object())
        return jsonify({"ok": True})
    except Exception as exc:
        current_app.logger.error("Manual sync failed: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 502


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _setting(key: str) -> str:
    """Resolve a setting from the config file."""
    return _cfg(current_app._get_current_object(), key)
