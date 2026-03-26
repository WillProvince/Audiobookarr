import atexit
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config_object="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app.logger.setLevel(logging.INFO)

    from app.logging_setup import ring_handler

    root_logger = logging.getLogger()
    if ring_handler not in root_logger.handlers:
        ring_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(ring_handler)

    db.init_app(app)

    from app.routes.books import books_bp
    from app.routes.logs import logs_bp
    from app.routes.settings import settings_bp

    app.register_blueprint(books_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(logs_bp)

    with app.app_context():
        db.create_all()

    # Start background scheduler (not in testing)
    if not app.config.get("TESTING"):
        from apscheduler.schedulers.background import BackgroundScheduler

        from app.services.sync import sync_downloads

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=sync_downloads,
            args=[app],
            trigger="interval",
            seconds=60,
            id="sync_downloads",
            replace_existing=True,
        )
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown(wait=False))

    return app
