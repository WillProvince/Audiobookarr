"""Post-download file importer: moves completed audiobook files to the library."""

import logging
import os
import re
import shutil

logger = logging.getLogger(__name__)

# Audio file extensions we recognise as the actual audiobook content
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".m4b", ".flac", ".ogg", ".opus", ".aac", ".wav"}


def _sanitize(value: str) -> str:
    """Remove characters that are unsafe in directory/file names."""
    value = value.strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"_+", "_", value)
    return value


def build_dest_dir(
    author: str,
    title: str,
    naming_format: str,
    audiobooks_path: str,
    *,
    series: str = "",
    series_index: str = "",
    narrator: str = "",
    year: str = "",
) -> str:
    """
    Resolve the destination directory for a book using the naming format.

    Supported tokens: {author}, {title}, {series}, {series_index}, {narrator}, {year}
    Example format:   "{author}/{title}"  →  /audiobooks/Frank Herbert/Dune

    Empty token values produce empty strings; consecutive path separators that
    result from empty tokens are collapsed so that e.g. {author}/{series}/{title}
    with no series still yields a clean path.
    """
    safe_author = _sanitize(author)
    safe_title = _sanitize(title)
    safe_series = _sanitize(series or "")
    safe_series_index = _sanitize(series_index or "")
    safe_narrator = _sanitize(narrator or "")
    safe_year = _sanitize(year or "")
    try:
        relative = naming_format.format(
            author=safe_author,
            title=safe_title,
            series=safe_series,
            series_index=safe_series_index,
            narrator=safe_narrator,
            year=safe_year,
        )
    except KeyError as exc:
        logger.warning("Unknown naming token %s – falling back to '{author}/{title}'", exc)
        relative = f"{safe_author}/{safe_title}"
    # Collapse consecutive separators that arise from empty token substitutions
    parts = [p for p in relative.replace("\\", "/").split("/") if p]
    relative = os.path.join(*parts) if parts else f"{safe_author}{os.sep}{safe_title}"
    return os.path.join(audiobooks_path, relative)


def _find_source_dir(content_path: str, torrent_name: str, library_path: str) -> str | None:
    """
    Determine the directory that contains the downloaded files.

    qBittorrent's content_path field points to:
    - The single file itself   (single-file torrent)
    - The torrent root folder  (multi-file torrent)

    We return the directory in both cases so we can scan for audio files.

    Priority when library_path is configured:
    1. library_path/torrent_name exact match  (the user-configured save path)
    2. Fuzzy subdirectory scan of library_path
    3. content_path directly (qBittorrent-reported path, used as fallback)
    4. Parent of content_path
    """
    if library_path and os.path.isdir(library_path):
        # 1. Exact match on torrent name under the configured library path
        if torrent_name:
            candidate = os.path.join(library_path, torrent_name)
            if os.path.isdir(candidate):
                return candidate

        # 2. Fuzzy match: find any subdirectory of library_path whose name is a
        #    substring of torrent_name or vice-versa.  Require a minimum length
        #    to avoid spurious matches on short strings like "A" or "The".
        _FUZZY_MIN_LEN = 8
        if torrent_name:
            torrent_lower = torrent_name.lower()
            matches = []
            try:
                for entry in os.scandir(library_path):
                    if entry.is_dir():
                        name_lower = entry.name.lower()
                        if len(name_lower) >= _FUZZY_MIN_LEN and name_lower in torrent_lower:
                            matches.append(entry.path)
                        elif len(torrent_lower) >= _FUZZY_MIN_LEN and torrent_lower in name_lower:
                            matches.append(entry.path)
            except OSError:
                pass
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                logger.warning(
                    "_find_source_dir: multiple fuzzy-match candidates for %r: %s — skipping",
                    torrent_name, matches,
                )

    # 3. Try content_path directly (fallback when no library_path or no match found)
    if content_path and os.path.exists(content_path):
        if os.path.isdir(content_path):
            return content_path
        return os.path.dirname(content_path)

    # 4. Try parent of content_path (in case it's a file path and parent exists)
    if content_path:
        parent = os.path.dirname(content_path)
        if parent and os.path.isdir(parent):
            return parent

    return None


def import_download(
    author: str,
    title: str,
    content_path: str,
    torrent_name: str,
    library_path: str,
    audiobooks_path: str,
    naming_format: str,
    *,
    series: str = "",
    series_index: str = "",
    narrator: str = "",
    year: str = "",
) -> str | None:
    """
    Move a completed download into the audiobook library.

    Returns the destination directory path on success, or None if nothing was moved.
    """
    source_dir = _find_source_dir(content_path, torrent_name, library_path)
    if not source_dir:
        logger.warning(
            "import_download: cannot locate source directory for %r (content_path=%r, library_path=%r)",
            torrent_name, content_path, library_path,
        )
        return None

    dest_dir = build_dest_dir(
        author, title, naming_format, audiobooks_path,
        series=series, series_index=series_index,
        narrator=narrator, year=year,
    )
    logger.info("import_download: %r → %r", source_dir, dest_dir)

    os.makedirs(dest_dir, exist_ok=True)

    moved_any = False
    for root, _dirs, files in os.walk(source_dir):
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in AUDIO_EXTENSIONS:
                continue
            src_file = os.path.join(root, filename)
            dst_file = os.path.join(dest_dir, filename)
            # Avoid overwriting if a file with the same name already exists
            if os.path.exists(dst_file):
                base, extension = os.path.splitext(filename)
                dst_file = os.path.join(dest_dir, f"{base}_1{extension}")
            try:
                shutil.move(src_file, dst_file)
                logger.info("import_download: moved %r → %r", src_file, dst_file)
                moved_any = True
            except OSError as exc:
                logger.error("import_download: failed to move %r: %s", src_file, exc)

    if not moved_any:
        logger.warning(
            "import_download: no audio files found in %r for book %r by %r",
            source_dir, title, author,
        )
        return None

    return dest_dir
