"""Tests for the post-download file importer service."""
import os
import shutil
import tempfile

import pytest

from app.services.importer import (
    AUDIO_EXTENSIONS,
    _find_source_dir,
    _sanitize,
    build_dest_dir,
    import_download,
)


# ---------------------------------------------------------------------------
# _sanitize
# ---------------------------------------------------------------------------


def test_sanitize_strips_unsafe_characters():
    assert _sanitize('Frank: "Herbert"') == "Frank_ _Herbert_"


def test_sanitize_strips_leading_trailing_whitespace():
    assert _sanitize("  Dune  ") == "Dune"


def test_sanitize_collapses_multiple_underscores():
    assert _sanitize("A<>B") == "A_B"


def test_sanitize_safe_string_unchanged():
    assert _sanitize("Frank Herbert") == "Frank Herbert"


# ---------------------------------------------------------------------------
# build_dest_dir
# ---------------------------------------------------------------------------


def test_build_dest_dir_default_format():
    result = build_dest_dir("Frank Herbert", "Dune", "{author}/{title}", "/audiobooks")
    assert result == "/audiobooks/Frank Herbert/Dune"


def test_build_dest_dir_flat_format():
    result = build_dest_dir("Frank Herbert", "Dune", "{author} - {title}", "/audiobooks")
    assert result == "/audiobooks/Frank Herbert - Dune"


def test_build_dest_dir_sanitizes_author_and_title():
    result = build_dest_dir('Frank: "Herbert"', "Dune/Part One", "{author}/{title}", "/audiobooks")
    assert ":" not in result
    assert '"' not in result
    assert result.startswith("/audiobooks/")


def test_build_dest_dir_unknown_token_falls_back():
    """An unrecognised token should fall back to {author}/{title}."""
    result = build_dest_dir("Frank Herbert", "Dune", "{author}/{title}/{unknown}", "/audiobooks")
    assert result == "/audiobooks/Frank Herbert/Dune"


# ---------------------------------------------------------------------------
# _find_source_dir
# ---------------------------------------------------------------------------


def test_find_source_dir_content_path_is_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = _find_source_dir(tmpdir, "some torrent", "")
        assert result == tmpdir


def test_find_source_dir_content_path_is_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        f = os.path.join(tmpdir, "book.mp3")
        open(f, "w").close()
        result = _find_source_dir(f, "some torrent", "")
        assert result == tmpdir


def test_find_source_dir_falls_back_to_library_path():
    with tempfile.TemporaryDirectory() as library_dir:
        torrent_name = "My Torrent"
        torrent_dir = os.path.join(library_dir, torrent_name)
        os.makedirs(torrent_dir)
        result = _find_source_dir("", torrent_name, library_dir)
        assert result == torrent_dir


def test_find_source_dir_returns_none_when_not_found():
    result = _find_source_dir("/nonexistent/path", "unknown torrent", "/also/nonexistent")
    assert result is None


def test_find_source_dir_falls_back_to_parent_of_nonexistent_file():
    """If content_path doesn't exist but its parent dir does, return the parent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        missing_file = os.path.join(tmpdir, "moved_file.mp3")
        # missing_file does not exist, but tmpdir does
        result = _find_source_dir(missing_file, "some torrent", "")
        assert result == tmpdir


def test_find_source_dir_fuzzy_match_subdir():
    """Fuzzy match: directory name is a substring of torrent_name."""
    with tempfile.TemporaryDirectory() as library_dir:
        # Directory on disk uses just the title; torrent_name has "Author - Title (Series)"
        actual_dir = os.path.join(library_dir, "A Court of Mist and Fury")
        os.makedirs(actual_dir)
        torrent_name = "Sarah J. Maas - A Court of Mist and Fury (A Court of Thorns and Roses #2)"
        result = _find_source_dir("", torrent_name, library_dir)
        assert result == actual_dir


def test_find_source_dir_fuzzy_match_torrent_in_dirname():
    """Fuzzy match: torrent_name is substring of directory name."""
    with tempfile.TemporaryDirectory() as library_dir:
        actual_dir = os.path.join(library_dir, "Dune Frank Herbert Unabridged Complete")
        os.makedirs(actual_dir)
        torrent_name = "Dune Frank Herbert"
        result = _find_source_dir("", torrent_name, library_dir)
        assert result == actual_dir


def test_find_source_dir_library_path_preferred_over_content_path():
    """library_path/torrent_name is preferred over content_path when both exist on disk."""
    with tempfile.TemporaryDirectory() as library_dir, \
         tempfile.TemporaryDirectory() as tmp_dir:
        # Simulate qBittorrent's temp folder (content_path)
        torrent_name = "Sarah J. Maas - Throne of Glass 3 - Heir of Fire"
        content_path = os.path.join(tmp_dir, torrent_name)
        os.makedirs(content_path)

        # Simulate the final configured save path (library_path/torrent_name)
        library_subdir = os.path.join(library_dir, torrent_name)
        os.makedirs(library_subdir)

        result = _find_source_dir(content_path, torrent_name, library_dir)

        # The configured library path must win over the raw content_path
        assert result == library_subdir


# ---------------------------------------------------------------------------
# import_download — successful move
# ---------------------------------------------------------------------------


def test_import_download_moves_audio_files():
    with tempfile.TemporaryDirectory() as src_dir, \
         tempfile.TemporaryDirectory() as audiobooks_dir:

        # Create a fake audio file in source dir
        audio_file = os.path.join(src_dir, "chapter1.mp3")
        with open(audio_file, "w") as f:
            f.write("fake audio data")

        dest = import_download(
            author="Frank Herbert",
            title="Dune",
            content_path=src_dir,
            torrent_name="Dune Frank Herbert",
            library_path="",
            audiobooks_path=audiobooks_dir,
            naming_format="{author}/{title}",
        )

        assert dest is not None
        assert dest == os.path.join(audiobooks_dir, "Frank Herbert", "Dune")
        assert os.path.exists(os.path.join(dest, "chapter1.mp3"))
        assert not os.path.exists(audio_file)


def test_import_download_ignores_non_audio_files():
    with tempfile.TemporaryDirectory() as src_dir, \
         tempfile.TemporaryDirectory() as audiobooks_dir:

        # Create a non-audio file
        txt_file = os.path.join(src_dir, "readme.txt")
        with open(txt_file, "w") as f:
            f.write("not audio")

        dest = import_download(
            author="Frank Herbert",
            title="Dune",
            content_path=src_dir,
            torrent_name="Dune Frank Herbert",
            library_path="",
            audiobooks_path=audiobooks_dir,
            naming_format="{author}/{title}",
        )

        # No audio files → returns None
        assert dest is None
        # Non-audio file should remain in source
        assert os.path.exists(txt_file)


def test_import_download_handles_filename_collision():
    with tempfile.TemporaryDirectory() as src_dir, \
         tempfile.TemporaryDirectory() as audiobooks_dir:

        # Pre-create dest dir with existing file
        dest_dir = os.path.join(audiobooks_dir, "Frank Herbert", "Dune")
        os.makedirs(dest_dir)
        existing = os.path.join(dest_dir, "chapter1.mp3")
        with open(existing, "w") as f:
            f.write("existing")

        # Source has same filename
        audio_file = os.path.join(src_dir, "chapter1.mp3")
        with open(audio_file, "w") as f:
            f.write("new audio data")

        dest = import_download(
            author="Frank Herbert",
            title="Dune",
            content_path=src_dir,
            torrent_name="Dune Frank Herbert",
            library_path="",
            audiobooks_path=audiobooks_dir,
            naming_format="{author}/{title}",
        )

        assert dest is not None
        # Original file should be untouched
        assert os.path.exists(existing)
        # New file should be renamed
        assert os.path.exists(os.path.join(dest_dir, "chapter1_1.mp3"))


def test_import_download_returns_none_when_source_not_found():
    with tempfile.TemporaryDirectory() as audiobooks_dir:
        dest = import_download(
            author="Frank Herbert",
            title="Dune",
            content_path="/nonexistent/path",
            torrent_name="unknown torrent",
            library_path="/also/nonexistent",
            audiobooks_path=audiobooks_dir,
            naming_format="{author}/{title}",
        )
        assert dest is None


def test_import_download_walks_subdirectories():
    """Audio files in subdirectories should also be moved."""
    with tempfile.TemporaryDirectory() as src_dir, \
         tempfile.TemporaryDirectory() as audiobooks_dir:

        sub_dir = os.path.join(src_dir, "disc1")
        os.makedirs(sub_dir)
        audio_file = os.path.join(sub_dir, "track01.m4b")
        with open(audio_file, "w") as f:
            f.write("fake m4b data")

        dest = import_download(
            author="Terry Pratchett",
            title="Guards Guards",
            content_path=src_dir,
            torrent_name="Guards Guards Terry Pratchett",
            library_path="",
            audiobooks_path=audiobooks_dir,
            naming_format="{author}/{title}",
        )

        assert dest is not None
        assert os.path.exists(os.path.join(dest, "track01.m4b"))
