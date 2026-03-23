"""Tests for the Flask routes (books and settings)."""
import json
import pytest
import responses as resp_lib

from app.models import Book, Download, Setting
from app.services.book_search import OPEN_LIBRARY_SEARCH_URL


# ---------------------------------------------------------------------------
# Books routes
# ---------------------------------------------------------------------------

def test_index_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Audiobookarr" in resp.data


def test_search_page(client):
    resp = client.get("/search")
    assert resp.status_code == 200
    assert b"Search" in resp.data


@resp_lib.activate
def test_api_search(client):
    resp_lib.add(
        resp_lib.GET,
        OPEN_LIBRARY_SEARCH_URL,
        json={"docs": [{"key": "/works/OL1W", "title": "Test Book", "author_name": ["Author"]}]},
        status=200,
    )
    resp = client.get("/api/search?q=test")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert isinstance(data, list)
    assert data[0]["title"] == "Test Book"


def test_api_search_missing_query(client):
    resp = client.get("/api/search")
    assert resp.status_code == 400


def test_api_add_book(client):
    resp = client.post(
        "/api/books",
        data=json.dumps({"title": "Dune", "author": "Frank Herbert"}),
        content_type="application/json",
    )
    assert resp.status_code == 201
    data = json.loads(resp.data)
    assert data["title"] == "Dune"
    assert data["status"] == "wanted"


def test_api_add_book_duplicate(client, app):
    with app.app_context():
        book = Book(title="Dune", author="Frank Herbert", open_library_id="/works/OL1W")
        from app import db
        db.session.add(book)
        db.session.commit()

    resp = client.post(
        "/api/books",
        data=json.dumps({"title": "Dune", "author": "Frank Herbert", "open_library_id": "/works/OL1W"}),
        content_type="application/json",
    )
    assert resp.status_code == 409


def test_api_add_book_missing_fields(client):
    resp = client.post(
        "/api/books",
        data=json.dumps({"title": "Dune"}),
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_api_list_books(client, app):
    with app.app_context():
        from app import db
        db.session.add(Book(title="Book A", author="Author A"))
        db.session.commit()

    resp = client.get("/api/books")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert any(b["title"] == "Book A" for b in data)


def test_api_delete_book(client, app):
    with app.app_context():
        from app import db
        book = Book(title="To Delete", author="Someone")
        db.session.add(book)
        db.session.commit()
        book_id = book.id

    resp = client.delete(f"/api/books/{book_id}")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["deleted"] == book_id


def test_api_delete_book_not_found(client):
    resp = client.delete("/api/books/99999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Jackett torrent search route
# ---------------------------------------------------------------------------

@resp_lib.activate
def test_api_search_torrents(client, app):
    with app.app_context():
        from app import db
        book = Book(title="Dune", author="Frank Herbert")
        db.session.add(book)
        db.session.commit()
        book_id = book.id

    resp_lib.add(
        resp_lib.GET,
        "http://jackett.test/api/v2.0/indexers/all/results",
        json={"Results": [{"Title": "Dune Audiobook", "Tracker": "idx", "Seeders": 10, "Size": 500000000, "MagnetUri": "magnet:?", "Link": ""}]},
        status=200,
    )

    resp = client.get(f"/api/books/{book_id}/torrents")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data[0]["title"] == "Dune Audiobook"


# ---------------------------------------------------------------------------
# qBittorrent download route
# ---------------------------------------------------------------------------

@resp_lib.activate
def test_api_download(client, app):
    with app.app_context():
        from app import db
        book = Book(title="Dune", author="Frank Herbert")
        db.session.add(book)
        db.session.commit()
        book_id = book.id

    resp_lib.add(resp_lib.POST, "http://qbt.test/api/v2/auth/login", body="Ok.", status=200)
    resp_lib.add(resp_lib.POST, "http://qbt.test/api/v2/torrents/add", body="Ok.", status=200)
    resp_lib.add(resp_lib.POST, "http://qbt.test/api/v2/auth/logout", body="", status=200)

    resp = client.post(
        f"/api/books/{book_id}/download",
        data=json.dumps({"magnet_or_url": "magnet:?xt=urn:btih:abc", "title": "Dune Audiobook", "indexer": "idx"}),
        content_type="application/json",
    )
    assert resp.status_code == 201
    data = json.loads(resp.data)
    assert data["status"] == "queued"


def test_api_download_missing_magnet(client, app):
    with app.app_context():
        from app import db
        book = Book(title="Dune", author="Frank Herbert")
        db.session.add(book)
        db.session.commit()
        book_id = book.id

    resp = client.post(
        f"/api/books/{book_id}/download",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Settings routes
# ---------------------------------------------------------------------------

def test_settings_page(client):
    resp = client.get("/settings")
    assert resp.status_code == 200
    assert b"Jackett" in resp.data
    assert b"qBittorrent" in resp.data


def test_api_save_and_get_settings(client):
    resp = client.post(
        "/api/settings",
        data=json.dumps({"JACKETT_URL": "http://new-jackett:9117", "JACKETT_API_KEY": "newkey"}),
        content_type="application/json",
    )
    assert resp.status_code == 200

    resp2 = client.get("/api/settings")
    data = json.loads(resp2.data)
    assert data["JACKETT_URL"] == "http://new-jackett:9117"
    # API key should be masked
    assert data["JACKETT_API_KEY"] == "********"
