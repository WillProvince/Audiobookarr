"""qBittorrent Web API client."""

import logging
import urllib.parse

import requests

logger = logging.getLogger(__name__)

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
        logger.info("qBittorrent login attempt: %s", self.base_url)
        resp = self._session.post(
            url,
            data={"username": self.username, "password": self.password},
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.text.strip()
        logger.debug("qBittorrent login response: %r", body)
        if body.lower() == "fails.":
            raise QBittorrentError("qBittorrent login failed: invalid credentials")
        if body.lower() not in ("ok.", "ok"):
            raise QBittorrentError(f"qBittorrent login unexpected response: {body!r}")
        logger.info("qBittorrent login succeeded")
        self._logged_in = True

    def logout(self) -> None:
        if self._logged_in:
            logger.info("qBittorrent logout")
            try:
                self._session.post(self.base_url + LOGOUT_PATH, timeout=5)
            except requests.RequestException:
                pass
            self._logged_in = False

    def _ensure_logged_in(self) -> None:
        if not self._logged_in:
            self.login()

    def _post_with_reauth(self, url: str, data: dict, timeout: int = 15) -> requests.Response:
        """POST with automatic re-authentication on 403 (session expired)."""
        resp = self._session.post(url, data=data, timeout=timeout)
        if resp.status_code == 403:
            logger.warning("qBittorrent session expired, re-authenticating...")
            self._logged_in = False
            self.login()
            resp = self._session.post(url, data=data, timeout=timeout)
        return resp

    def _get_with_reauth(self, url: str, params: dict, timeout: int = 10) -> requests.Response:
        """GET with automatic re-authentication on 403 (session expired)."""
        resp = self._session.get(url, params=params, timeout=timeout)
        if resp.status_code == 403:
            logger.warning("qBittorrent session expired, re-authenticating...")
            self._logged_in = False
            self.login()
            resp = self._session.get(url, params=params, timeout=timeout)
        return resp

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
        logger.info("add_torrent called: magnet_or_url=%r save_path=%r", magnet_or_url, save_path)

        data: dict = {"category": category, "urls": magnet_or_url}
        if save_path:
            data["savepath"] = save_path

        resp = self._post_with_reauth(url, data=data, timeout=15)
        logger.debug("add_torrent response: status=%s body=%r", resp.status_code, resp.text)
        resp.raise_for_status()

        if resp.text.strip().lower() not in ("ok.", "ok"):
            logger.error("qBittorrent rejected torrent: %s", resp.text.strip())
            raise QBittorrentError(f"qBittorrent rejected torrent: {resp.text.strip()}")

        logger.info("add_torrent succeeded")

    def get_torrents(self, category: str = "audiobookarr") -> list[dict]:
        """Return a list of torrent info dicts for the given category."""
        self._ensure_logged_in()
        url = self.base_url + TORRENT_INFO_PATH
        params: dict = {}
        if category:
            params["category"] = category
        resp = self._get_with_reauth(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
