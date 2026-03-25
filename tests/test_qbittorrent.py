"""Tests for the qBittorrent client."""
import pytest
import responses as resp_lib

from app.services.qbittorrent import QBittorrentClient, QBittorrentError

BASE = "http://qbt.test"
LOGIN_URL = BASE + "/api/v2/auth/login"
ADD_URL = BASE + "/api/v2/torrents/add"
INFO_URL = BASE + "/api/v2/torrents/info"
LOGOUT_URL = BASE + "/api/v2/auth/logout"


@resp_lib.activate
def test_login_success():
    resp_lib.add(resp_lib.POST, LOGIN_URL, body="Ok.", status=200)
    client = QBittorrentClient(BASE, "admin", "adminadmin")
    client.login()
    assert client._logged_in is True


@resp_lib.activate
def test_login_failure_raises():
    resp_lib.add(resp_lib.POST, LOGIN_URL, body="Fails.", status=200)
    client = QBittorrentClient(BASE, "admin", "wrong")
    with pytest.raises(QBittorrentError):
        client.login()


@resp_lib.activate
def test_add_torrent_success():
    resp_lib.add(resp_lib.POST, LOGIN_URL, body="Ok.", status=200)
    resp_lib.add(resp_lib.POST, ADD_URL, body="Ok.", status=200)
    resp_lib.add(resp_lib.POST, LOGOUT_URL, body="", status=200)

    client = QBittorrentClient(BASE, "admin", "adminadmin")
    client.login()
    client.add_torrent("magnet:?xt=urn:btih:abc123")
    client.logout()
    assert not client._logged_in


@resp_lib.activate
def test_add_torrent_auto_login():
    """Client should auto-login if not already logged in."""
    resp_lib.add(resp_lib.POST, LOGIN_URL, body="Ok.", status=200)
    resp_lib.add(resp_lib.POST, ADD_URL, body="Ok.", status=200)

    client = QBittorrentClient(BASE, "admin", "adminadmin")
    client.add_torrent("magnet:?xt=urn:btih:abc123")
    assert client._logged_in is True


@resp_lib.activate
def test_add_torrent_rejected_raises():
    resp_lib.add(resp_lib.POST, LOGIN_URL, body="Ok.", status=200)
    resp_lib.add(resp_lib.POST, ADD_URL, body="Fails.", status=200)

    client = QBittorrentClient(BASE, "admin", "adminadmin")
    client.login()
    with pytest.raises(QBittorrentError):
        client.add_torrent("magnet:?xt=urn:btih:abc123")


@resp_lib.activate
def test_get_torrents():
    fake_torrents = [{"hash": "abc", "name": "My Book", "state": "seeding"}]
    resp_lib.add(resp_lib.POST, LOGIN_URL, body="Ok.", status=200)
    resp_lib.add(resp_lib.GET, INFO_URL, json=fake_torrents, status=200)

    client = QBittorrentClient(BASE, "admin", "adminadmin")
    client.login()
    result = client.get_torrents()
    assert result == fake_torrents


@resp_lib.activate
def test_add_torrent_reauth_on_403():
    """add_torrent should re-authenticate and retry when the first POST returns 403."""
    resp_lib.add(resp_lib.POST, LOGIN_URL, body="Ok.", status=200)
    # First add attempt returns 403 (session expired)
    resp_lib.add(resp_lib.POST, ADD_URL, body="", status=403)
    # Re-auth login
    resp_lib.add(resp_lib.POST, LOGIN_URL, body="Ok.", status=200)
    # Retry succeeds
    resp_lib.add(resp_lib.POST, ADD_URL, body="Ok.", status=200)

    client = QBittorrentClient(BASE, "admin", "adminadmin")
    client.login()
    client.add_torrent("magnet:?xt=urn:btih:abc123")
    assert client._logged_in is True


@resp_lib.activate
def test_login_unexpected_response_raises():
    """login() should raise QBittorrentError when the response body is unexpected."""
    resp_lib.add(resp_lib.POST, LOGIN_URL, body="SomeUnexpectedBody", status=200)
    client = QBittorrentClient(BASE, "admin", "adminadmin")
    with pytest.raises(QBittorrentError):
        client.login()
