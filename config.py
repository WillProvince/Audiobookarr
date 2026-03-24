import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'audiobookarr.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Jackett settings
    JACKETT_URL = os.environ.get("JACKETT_URL", "http://localhost:9117")
    JACKETT_API_KEY = os.environ.get("JACKETT_API_KEY", "")
    JACKETT_INDEXER = os.environ.get("JACKETT_INDEXER", "all")

    # qBittorrent settings
    QBITTORRENT_URL = os.environ.get("QBITTORRENT_URL", "http://localhost:8080")
    QBITTORRENT_USERNAME = os.environ.get("QBITTORRENT_USERNAME", "admin")
    QBITTORRENT_PASSWORD = os.environ.get("QBITTORRENT_PASSWORD", "adminadmin")
    QBITTORRENT_SAVE_PATH = os.environ.get("QBITTORRENT_SAVE_PATH", "")

    # Audiobook category IDs used for Jackett/Newznab (3030 = AudioBook)
    JACKETT_CATEGORIES = os.environ.get("JACKETT_CATEGORIES", "3030")

    # Path inside the container where downloaded files are accessible
    LIBRARY_PATH = os.environ.get("LIBRARY_PATH", "/downloads")
