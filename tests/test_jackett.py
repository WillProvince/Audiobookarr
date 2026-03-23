"""Tests for the Jackett torrent search service."""
import pytest
import responses as resp_lib

from app.services.jackett import search_torrents

JACKETT_BASE = "http://jackett.test"
JACKETT_KEY = "testkey"


def _jackett_url(indexer="all"):
    return f"{JACKETT_BASE}/api/v2.0/indexers/{indexer}/results"


@resp_lib.activate
def test_search_returns_sorted_results():
    resp_lib.add(
        resp_lib.GET,
        _jackett_url(),
        json={
            "Results": [
                {"Title": "Low Seeds", "Tracker": "idx1", "Seeders": 1, "Size": 100000000, "MagnetUri": "magnet:?xt=1", "Link": ""},
                {"Title": "High Seeds", "Tracker": "idx2", "Seeders": 50, "Size": 500000000, "MagnetUri": "magnet:?xt=2", "Link": ""},
            ]
        },
        status=200,
    )

    results = search_torrents(JACKETT_BASE, JACKETT_KEY, "test query")
    # Should be sorted by seeders descending
    assert results[0]["title"] == "High Seeds"
    assert results[0]["seeders"] == 50
    assert results[1]["title"] == "Low Seeds"


@resp_lib.activate
def test_search_empty_results():
    resp_lib.add(resp_lib.GET, _jackett_url(), json={"Results": []}, status=200)
    results = search_torrents(JACKETT_BASE, JACKETT_KEY, "nothing")
    assert results == []


@resp_lib.activate
def test_search_custom_indexer():
    resp_lib.add(resp_lib.GET, _jackett_url("myindexer"), json={"Results": []}, status=200)
    search_torrents(JACKETT_BASE, JACKETT_KEY, "test", indexer="myindexer")
    assert resp_lib.calls[0].request.url.startswith(
        f"{JACKETT_BASE}/api/v2.0/indexers/myindexer/results"
    )


@resp_lib.activate
def test_search_http_error_raises():
    resp_lib.add(resp_lib.GET, _jackett_url(), status=403, body="Forbidden")
    with pytest.raises(Exception):
        search_torrents(JACKETT_BASE, JACKETT_KEY, "fail test")
