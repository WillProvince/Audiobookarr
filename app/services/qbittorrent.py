"""qBittorrent Web API client."""

import urllib.parse

import requests

LOGIN_PATH = "/api/v2/auth/login"
ADD_TORRENT_PATH = "/api/v2/torrents/add"
TORRENT_INFO_PATH = "/api/v2/torrents/info"
LOGOUT_PATH = "/api/v2/auth/logout"

_ALLOWED_SCHEMES = {"http", "https"}


def _validate_url(url: str) -> None:
    """Raise ValueError if *url* is not a safe http/https URL."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"qBittorrent URL must use http or https, got: {parsed.scheme!r}")
    if not parsed.netloc:
        raise ValueError(f"qBittorrent URL has no host: {url!r}")


class QBittorrentError(Exception):
    pass


class QBittorrentClient:
    """Minimal qBittorrent Web API client using a requests session."""

    def __init__(self, base_url: str, username: str, password: str):
        _validate_url(base_url)
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._session = requests.Session()
        self._logged_in = False

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def login(self) -> None:
        """Authenticate with qBittorrent.  Raises QBittorrentError on failure."""
        url = self.base_url + LOGIN_PATH
        resp = self._session.post(
            url,
            data={"username": self.username, "password": self.password},
            timeout=10,
        )
        resp.raise_for_status()
        if resp.text.strip() == "Fails.":
            raise QBittorrentError("qBittorrent login failed: invalid credentials")
        self._logged_in = True

    def logout(self) -> None:
        if self._logged_in:
            try:
                self._session.post(self.base_url + LOGOUT_PATH, timeout=5)
            except requests.RequestException:
                pass
            self._logged_in = False

    def _ensure_logged_in(self) -> None:
        if not self._logged_in:
            self.login()

    # ------------------------------------------------------------------
    # Torrent management
    # ------------------------------------------------------------------

    def add_torrent(
        self,
        magnet_or_url: str,
        save_path: str = "",
        category: str = "audiobookarr",
    ) -> None:
        """Add a torrent by magnet link or URL.

        Args:
            magnet_or_url: Magnet URI or HTTP URL of the .torrent file.
            save_path:     Directory where the torrent should be saved.
            category:      qBittorrent category/label.

        Raises:
            QBittorrentError: If the request fails or qBittorrent reports an error.
        """
        self._ensure_logged_in()
        url = self.base_url + ADD_TORRENT_PATH

        data: dict = {"category": category}
        if save_path:
            data["savepath"] = save_path

        if magnet_or_url.startswith("magnet:"):
            data["urls"] = magnet_or_url
        else:
            data["urls"] = magnet_or_url

        resp = self._session.post(url, data=data, timeout=15)
        resp.raise_for_status()

        if resp.text.strip().lower() not in ("ok.", "ok"):
            raise QBittorrentError(f"qBittorrent rejected torrent: {resp.text.strip()}")

    def get_torrents(self, category: str = "audiobookarr") -> list[dict]:
        """Return a list of torrent info dicts for the given category."""
        self._ensure_logged_in()
        url = self.base_url + TORRENT_INFO_PATH
        params: dict = {}
        if category:
            params["category"] = category
        resp = self._session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
