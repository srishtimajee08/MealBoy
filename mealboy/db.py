"""Small, explicit SQLite data layer. All personal queries require an owner ID."""

import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db():
    if "db" not in g:
        connection = sqlite3.connect(current_app.config["DATABASE"], timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def init_app(app):
    @app.teardown_appcontext
    def close_db(_error):
        connection = g.pop("db", None)
        if connection is not None:
            connection.close()

    with app.app_context():
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        get_db().executescript(schema)
        get_db().commit()
