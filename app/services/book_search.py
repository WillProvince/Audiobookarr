"""Book search service using the Open Library API and iTunes Search API."""

import requests

OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
OPEN_LIBRARY_COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"


def search_books(query: str, limit: int = 20) -> list[dict]:
    """Search Open Library for books matching *query*.

    Returns a list of dicts with keys:
        title, author, open_library_id, cover_url
    """
    params = {
        "q": query,
        "fields": "key,title,author_name,cover_i,first_publish_year",
        "limit": limit,
    }
    response = requests.get(OPEN_LIBRARY_SEARCH_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    results = []
    for doc in data.get("docs", []):
        cover_id = doc.get("cover_i")
        cover_url = OPEN_LIBRARY_COVER_URL.format(cover_id=cover_id) if cover_id else None

        authors = doc.get("author_name", [])
        author = ", ".join(authors) if authors else "Unknown"

        # Open Library work key looks like /works/OL12345W
        ol_key = doc.get("key", "")

        results.append(
            {
                "title": doc.get("title", "Unknown Title"),
                "author": author,
                "open_library_id": ol_key,
                "cover_url": cover_url,
                "first_publish_year": doc.get("first_publish_year"),
            }
        )
    return results
