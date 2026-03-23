"""Shared pytest fixtures."""
import pytest

from app import create_app, db as _db


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "test-secret"
    JACKETT_URL = "http://jackett.test"
    JACKETT_API_KEY = "testkey"
    JACKETT_INDEXER = "all"
    JACKETT_CATEGORIES = "3030"
    QBITTORRENT_URL = "http://qbt.test"
    QBITTORRENT_USERNAME = "admin"
    QBITTORRENT_PASSWORD = "adminadmin"
    QBITTORRENT_SAVE_PATH = ""


@pytest.fixture
def app():
    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
