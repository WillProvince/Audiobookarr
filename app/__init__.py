from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_object="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)

    from app.routes.books import books_bp
    from app.routes.settings import settings_bp

    app.register_blueprint(books_bp)
    app.register_blueprint(settings_bp)

    with app.app_context():
        db.create_all()

    return app
