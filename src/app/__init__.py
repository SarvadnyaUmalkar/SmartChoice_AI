"""
SmartChoice AI — Application Factory
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_object: str = "app.config.Config") -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config.from_object(config_object)

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    limiter.init_app(app)

    # ── Logging ───────────────────────────────────────────────────────────────
    _configure_logging(app)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.blueprints.chat.routes import chat_bp
    from app.blueprints.decisions.routes import decisions_bp
    from app.blueprints.history.routes import history_bp
    from app.blueprints.reports.routes import reports_bp
    from app.blueprints.main.routes import main_bp  # noqa: E402

    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    app.register_blueprint(decisions_bp, url_prefix="/api/decisions")
    app.register_blueprint(history_bp, url_prefix="/api/history")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")

    # ── DB tables ─────────────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()

    # ── Custom error handlers ─────────────────────────────────────────────────
    _register_error_handlers(app)

    app.logger.info("SmartChoice AI started successfully.")
    return app


def _configure_logging(app: Flask) -> None:
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    log_file = app.config.get("LOG_FILE", "logs/smartchoice.log")
    # Use absolute path so RotatingFileHandler never fails on relative dirs
    if not os.path.isabs(log_file):
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", log_file)
    log_file = os.path.normpath(log_file)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=app.config.get("LOG_MAX_BYTES", 10_485_760),
        backupCount=app.config.get("LOG_BACKUP_COUNT", 5),
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(log_level)

    app.logger.addHandler(file_handler)
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(log_level)


def _register_error_handlers(app: Flask) -> None:
    from flask import jsonify

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error="Bad Request", message=str(e)), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="Not Found", message=str(e)), 404

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify(error="Too Many Requests", message="Rate limit exceeded. Please wait."), 429

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception("Internal server error: %s", e)
        return jsonify(error="Internal Server Error", message="Something went wrong."), 500
