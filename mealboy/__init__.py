"""Application factory: configuration and shared request protections."""

import os
import secrets
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, g, jsonify, request, session
from werkzeug.exceptions import HTTPException

from . import db

ROOT = Path(__file__).resolve().parent.parent


def create_app(test_config=None):
    load_dotenv(ROOT / ".env")
    app = Flask(__name__, instance_path=str(ROOT / "instance"))
    app.config.from_mapping(
        DATABASE=str(ROOT / "instance" / "mealboy.sqlite3"),
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        MODEL_PATH=str(ROOT / os.getenv("MODEL_PATH", "artifacts/food_model.keras")),
        MODEL_LABELS_PATH=str(ROOT / os.getenv("MODEL_LABELS_PATH", "artifacts/labels.json")),
        CHAT_PROVIDER=os.getenv("CHAT_PROVIDER", "extractive"),
        OLLAMA_URL=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
        OLLAMA_MODEL=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        DEFAULT_TIMEZONE=os.getenv("MEALBOY_TIMEZONE", "Asia/Kolkata"),
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    secret_file = ROOT / "instance" / ".secret"
    secret = app.config.get("SECRET_KEY") or os.getenv("SECRET_KEY")
    if not secret:
        try:
            with secret_file.open("x", encoding="utf-8") as stream:
                stream.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        secret = secret_file.read_text(encoding="utf-8").strip()
    app.config["SECRET_KEY"] = secret
    db.init_app(app)

    from .auth import auth
    from .routes import web

    app.register_blueprint(auth)
    app.register_blueprint(web)

    @app.before_request
    def protect_request():
        session.setdefault("csrf_token", secrets.token_urlsafe(32))
        g.user = None
        if session.get("user_id"):
            g.user = (
                db.get_db()
                .execute("SELECT * FROM users WHERE id = ?", (session["user_id"],))
                .fetchone()
            )
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
            if not secrets.compare_digest(session["csrf_token"], supplied):
                abort(400, description="Your session expired. Refresh the page and try again.")

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob: data:; "
            "style-src 'self'; script-src 'self'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if request.path.startswith("/api/"):
            return jsonify(error=error.description), error.code
        from flask import render_template

        return render_template("error.html", error=error), error.code

    return app
