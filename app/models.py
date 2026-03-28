from datetime import datetime, timezone
from app import db


class Book(db.Model):
    """A book that the user wants to track and download."""

    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    author = db.Column(db.String(500), nullable=False)
    open_library_id = db.Column(db.String(100), unique=True, nullable=True)
    cover_url = db.Column(db.String(1000), nullable=True)
    series = db.Column(db.String(500), nullable=True)
    series_index = db.Column(db.String(50), nullable=True)
    narrator = db.Column(db.String(500), nullable=True)
    year = db.Column(db.String(10), nullable=True)
    # Status: wanted | downloading | downloaded | missing
    status = db.Column(db.String(50), nullable=False, default="wanted")
    added_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    downloads = db.relationship("Download", backref="book", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "open_library_id": self.open_library_id,
            "cover_url": self.cover_url,
            "series": self.series,
            "series_index": self.series_index,
            "narrator": self.narrator,
            "year": self.year,
            "status": self.status,
            "added_at": self.added_at.isoformat(),
        }


class Download(db.Model):
    """A torrent download associated with a book."""

    __tablename__ = "downloads"

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    torrent_title = db.Column(db.String(1000), nullable=False)
    magnet_or_url = db.Column(db.String(2000), nullable=False)
    indexer = db.Column(db.String(200), nullable=True)
    # Status: queued | downloading | seeding | completed | error
    status = db.Column(db.String(50), nullable=False, default="queued")
    added_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    download_path = db.Column(db.String(2000), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "book_id": self.book_id,
            "torrent_title": self.torrent_title,
            "magnet_or_url": self.magnet_or_url,
            "indexer": self.indexer,
            "status": self.status,
            "added_at": self.added_at.isoformat(),
            "download_path": self.download_path,
        }
