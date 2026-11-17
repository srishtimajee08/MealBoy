"""Session authentication with password hashing, CSRF and login throttling."""

import hashlib
import re
import secrets
import sqlite3
import time
from functools import wraps

from flask import (
    Blueprint,
    abort,
    current_app,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db

auth = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            if request.path.startswith("/api/"):
                abort(401, description="Please sign in first.")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def throttle_auth(email):
    """Limit attempts by both account and IP; never trust forwarded IP headers."""
    connection = get_db()
    now = time.time()
    buckets = [f"email:{email}", f"ip:{request.remote_addr}"]
    with connection:
        connection.execute("DELETE FROM login_attempts WHERE attempted_at < ?", (now - 900,))
        for raw_bucket in buckets:
            bucket = hashlib.sha256(raw_bucket.encode()).hexdigest()
            count = connection.execute(
                "SELECT COUNT(*) FROM login_attempts WHERE bucket = ?", (bucket,)
            ).fetchone()[0]
            if count >= 20:
                abort(429, description="Too many sign-in attempts. Try again in 15 minutes.")
            connection.execute("INSERT INTO login_attempts VALUES (?, ?)", (bucket, now))


def start_session(user_id):
    session.clear()
    session["user_id"] = user_id
    session["csrf_token"] = secrets.token_urlsafe(32)
    session.permanent = True


@auth.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        throttle_auth(email)
        if not 2 <= len(name) <= 80:
            error = "Use a name between 2 and 80 characters."
        elif len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            error = "Enter a valid email address."
        elif not 10 <= len(password) <= 128:
            error = "Use a password between 10 and 128 characters."
        else:
            try:
                connection = get_db()
                with connection:
                    cursor = connection.execute(
                        "INSERT INTO users (name,email,password_hash,timezone) VALUES (?,?,?,?)",
                        (
                            name,
                            email,
                            generate_password_hash(password),
                            current_app.config["DEFAULT_TIMEZONE"],
                        ),
                    )
                start_session(cursor.lastrowid)
                return redirect(url_for("web.dashboard"))
            except sqlite3.IntegrityError:
                error = "Unable to create this account. Try signing in."
    return render_template("auth.html", registering=True, error=error)


@auth.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()[:254]
        password = request.form.get("password", "")[:129]
        throttle_auth(email)
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            start_session(user["id"])
            return redirect(url_for("web.dashboard"))
        error = "Email or password is incorrect."
    return render_template("auth.html", registering=False, error=error)


@auth.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
