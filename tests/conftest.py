"""Shared pytest fixtures."""
import json
import os
import tempfile

import pytest

from app import create_app, db as _db


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "test-secret"
    # Use a temp file so config_file.py has somewhere to write
    CONFIG_FILE = os.path.join(tempfile.mkdtemp(), "test_config.json")


@pytest.fixture
def app():
    cfg_file = TestConfig.CONFIG_FILE
    # Write test settings so routes can find Jackett/qBT URLs
    with open(cfg_file, "w") as f:
        json.dump({
            "JACKETT_URL": "http://jackett.test",
            "JACKETT_API_KEY": "testkey",
            "JACKETT_INDEXER": "all",
            "JACKETT_CATEGORIES": "3030",
            "QBITTORRENT_URL": "http://qbt.test",
            "QBITTORRENT_USERNAME": "admin",
            "QBITTORRENT_PASSWORD": "adminadmin",
            "QBITTORRENT_SAVE_PATH": "",
        }, f)
    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
