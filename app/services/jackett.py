"""Jackett indexer integration."""

import urllib.parse

import requests

JACKETT_SEARCH_PATH = "/api/v2.0/indexers/{indexer}/results"
_ALLOWED_SCHEMES = {"http", "https"}


def _validate_url(url: str) -> None:
    """Raise ValueError if *url* is not a safe http/https URL."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"Jackett URL must use http or https, got: {parsed.scheme!r}")
    if not parsed.netloc:
        raise ValueError(f"Jackett URL has no host: {url!r}")


def search_torrents(
    base_url: str,
    api_key: str,
    query: str,
    indexer: str = "all",
    categories: str = "3030",
    timeout: int = 30,
) -> list[dict]:
    """Search Jackett for torrents matching *query*.

    Args:
        base_url:   Jackett base URL, e.g. "http://localhost:9117".
        api_key:    Jackett API key.
        query:      Search term (typically "<title> <author>").
        indexer:    Jackett indexer slug to search (default "all").
        categories: Comma-separated Newznab category IDs (default "3030" = AudioBook).
        timeout:    Request timeout in seconds.

    Returns:
        List of dicts with keys: title, indexer, seeders, size, magnet_url, download_url.
    """
    _validate_url(base_url)
    url = base_url.rstrip("/") + JACKETT_SEARCH_PATH.format(indexer=indexer)
    params = {
        "apikey": api_key,
        "Query": query,
    }
    for cat in categories.split(","):
        cat = cat.strip()
        if cat:
            params.setdefault("Category[]", [])
            if isinstance(params["Category[]"], list):
                params["Category[]"].append(cat)

    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data.get("Results", []):
        results.append(
            {
                "title": item.get("Title", ""),
                "indexer": item.get("Tracker", ""),
                "seeders": item.get("Seeders", 0),
                "size": item.get("Size", 0),
                "magnet_url": item.get("MagnetUri", ""),
                "download_url": item.get("Link", ""),
            }
        )

    # Sort by seeders descending so the best result comes first
    results.sort(key=lambda x: x["seeders"], reverse=True)
    return results
