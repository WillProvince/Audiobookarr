import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'audiobookarr.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CONFIG_FILE = os.environ.get("CONFIG_FILE", "/data/config.json")
