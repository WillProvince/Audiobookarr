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

    def to_dict(self):
        return {
            "id": self.id,
            "book_id": self.book_id,
            "torrent_title": self.torrent_title,
            "magnet_or_url": self.magnet_or_url,
            "indexer": self.indexer,
            "status": self.status,
            "added_at": self.added_at.isoformat(),
        }


class Setting(db.Model):
    """Key-value store for application settings."""

    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(200), unique=True, nullable=False)
    value = db.Column(db.String(2000), nullable=True)

    @classmethod
    def get(cls, key, default=None):
        row = cls.query.filter_by(key=key).first()
        if row is None:
            return default
        return row.value

    @classmethod
    def set(cls, key, value):
        row = cls.query.filter_by(key=key).first()
        if row is None:
            row = cls(key=key, value=value)
            db.session.add(row)
        else:
            row.value = value
        db.session.commit()
