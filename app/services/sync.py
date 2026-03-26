"""Background sync: pull torrent statuses from qBittorrent and update the DB."""

import logging

from app import db
from app.models import Book, Download, Setting
from app.services.qbittorrent import QBittorrentClient

logger = logging.getLogger(__name__)

# Map qBittorrent torrent states to app Download states
_STATE_MAP = {
    "downloading": "downloading",
    "stalledDL": "downloading",
    "metaDL": "downloading",
    "checkingDL": "downloading",
    "forcedDL": "downloading",
    "pausedDL": "downloading",   # qBittorrent <5.x paused while downloading
    "stoppedDL": "downloading",  # qBittorrent 5.x renamed pausedDL → stoppedDL
    "uploading": "seeding",
    "stalledUP": "seeding",
    "seeding": "seeding",
    "forcedUP": "seeding",
    "checkingUP": "seeding",
    "queuedUP": "seeding",       # queued for seeding — download is complete
    "pausedUP": "completed",     # qBittorrent <5.x completed and paused
    "stoppedUP": "completed",    # qBittorrent 5.x renamed pausedUP → stoppedUP
    "completed": "completed",
    "error": "error",
    "missingFiles": "error",
    "unknown": "error",
}


def sync_downloads(app) -> None:
    """Sync download statuses from qBittorrent. Called by the scheduler."""
    with app.app_context():
        try:
            _do_sync()
        except Exception:
            logger.exception("sync_downloads: unexpected error")


def _setting(key: str) -> str:
    """Resolve a setting from the DB, falling back to the app config."""
    from flask import current_app

    from_db = Setting.get(key)
    if from_db is not None:
        return from_db
    return current_app.config.get(key, "")


def _do_sync() -> None:
    active = (
        Download.query.filter(
            Download.status.notin_(["completed", "error"])
        )
        .join(Book)
        .all()
    )

    if not active:
        logger.debug("sync_downloads: no active downloads, skipping")
        return

    qbt_url = _setting("QBITTORRENT_URL")
    qbt_user = _setting("QBITTORRENT_USERNAME")
    qbt_pass = _setting("QBITTORRENT_PASSWORD")

    client = QBittorrentClient(qbt_url, qbt_user, qbt_pass)
    try:
        torrents = client.get_torrents(category="audiobookarr")
    finally:
        client.logout()

    # Build lookup: lowercased torrent name → torrent dict
    torrent_by_name = {t["name"].lower(): t for t in torrents}

    updated = 0
    for download in active:
        # Find matching torrent by substring match on title
        match = None
        dl_title_lower = download.torrent_title.lower()
        for name_lower, torrent in torrent_by_name.items():
            if dl_title_lower in name_lower or name_lower in dl_title_lower:
                match = torrent
                break

        if match is None:
            logger.warning(
                "sync_downloads: download id=%s torrent_title=%r — no matching torrent found in qBittorrent (category=audiobookarr)",
                download.id, download.torrent_title,
            )
            continue

        qbt_state = match.get("state", "")
        new_status = _STATE_MAP.get(qbt_state)
        if new_status is None:
            logger.warning(
                "sync_downloads: download id=%s matched torrent %r but qbt state %r is not in state map — skipping",
                download.id, match.get("name"), qbt_state,
            )
            continue
        if new_status == download.status:
            continue

        logger.info(
            "sync_downloads: download id=%s %r → %r (qbt state=%r)",
            download.id, download.status, new_status, qbt_state,
        )
        download.status = new_status
        updated += 1

        # Capture where qBittorrent saved the files (content_path or save_path + name)
        content_path = match.get("content_path") or match.get("save_path", "")
        if content_path and not download.download_path:
            download.download_path = content_path

        # Update parent book status
        book = download.book
        if new_status == "completed":
            book.status = "downloaded"
            try:
                _run_import(download, book)
            except Exception:
                logger.exception(
                    "sync_downloads: _run_import failed for download id=%s — status still saved as completed",
                    download.id,
                )
        elif new_status == "error":
            book.status = "missing"

    db.session.commit()
    logger.info(
        "sync_downloads: checked %d download(s), updated %d", len(active), updated
    )


def _run_import(download: Download, book: Book) -> None:
    """Attempt to import the completed download into the audiobook library."""
    from app.services.importer import import_download

    audiobooks_path = _setting("AUDIOBOOKS_PATH")
    naming_format = _setting("NAMING_FORMAT")
    library_path = _setting("QBITTORRENT_SAVE_PATH")

    if not audiobooks_path:
        logger.info(
            "sync_downloads: AUDIOBOOKS_PATH not set, skipping import for download id=%s",
            download.id,
        )
        return

    if not naming_format:
        naming_format = "{author}/{title}"

    dest = import_download(
        author=book.author,
        title=book.title,
        content_path=download.download_path or "",
        torrent_name=download.torrent_title,
        library_path=library_path,
        audiobooks_path=audiobooks_path,
        naming_format=naming_format,
    )

    if dest:
        logger.info(
            "sync_downloads: import complete for book id=%s → %r", book.id, dest
        )
    else:
        logger.warning(
            "sync_downloads: import found no files for book id=%s (download id=%s)",
            book.id, download.id,
        )
