"""Tests for the Open Library book search service."""
import pytest
import responses as resp_lib

from app.services.book_search import search_books, OPEN_LIBRARY_SEARCH_URL


@resp_lib.activate
def test_search_returns_results():
    resp_lib.add(
        resp_lib.GET,
        OPEN_LIBRARY_SEARCH_URL,
        json={
            "docs": [
                {
                    "key": "/works/OL27516W",
                    "title": "The Hobbit",
                    "author_name": ["J.R.R. Tolkien"],
                    "cover_i": 8406786,
                    "first_publish_year": 1937,
                }
            ]
        },
        status=200,
    )

    results = search_books("hobbit")
    assert len(results) == 1
    book = results[0]
    assert book["title"] == "The Hobbit"
    assert book["author"] == "J.R.R. Tolkien"
    assert book["open_library_id"] == "/works/OL27516W"
    assert "8406786" in book["cover_url"]
    assert book["first_publish_year"] == 1937


@resp_lib.activate
def test_search_empty_results():
    resp_lib.add(
        resp_lib.GET,
        OPEN_LIBRARY_SEARCH_URL,
        json={"docs": []},
        status=200,
    )

    results = search_books("xyzzy_no_results")
    assert results == []


@resp_lib.activate
def test_search_missing_cover():
    resp_lib.add(
        resp_lib.GET,
        OPEN_LIBRARY_SEARCH_URL,
        json={
            "docs": [
                {
                    "key": "/works/OL99999W",
                    "title": "No Cover Book",
                    "author_name": ["Some Author"],
                    # no cover_i field
                }
            ]
        },
        status=200,
    )

    results = search_books("no cover")
    assert results[0]["cover_url"] is None


@resp_lib.activate
def test_search_multiple_authors():
    resp_lib.add(
        resp_lib.GET,
        OPEN_LIBRARY_SEARCH_URL,
        json={
            "docs": [
                {
                    "key": "/works/OL11111W",
                    "title": "Multi Author Book",
                    "author_name": ["Author One", "Author Two"],
                }
            ]
        },
        status=200,
    )

    results = search_books("multi")
    assert results[0]["author"] == "Author One, Author Two"


@resp_lib.activate
def test_search_http_error_raises():
    resp_lib.add(
        resp_lib.GET,
        OPEN_LIBRARY_SEARCH_URL,
        status=500,
        body="Internal Server Error",
    )

    with pytest.raises(Exception):
        search_books("error test")
