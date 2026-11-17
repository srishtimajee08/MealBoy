import pytest

from mealboy import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "DATABASE": str(tmp_path / "test.sqlite3"),
            "MODEL_PATH": str(tmp_path / "missing.keras"),
            "MODEL_LABELS_PATH": str(tmp_path / "missing.json"),
            "CHAT_PROVIDER": "extractive",
        }
    )


@pytest.fixture
def client(app):
    return app.test_client()


def csrf(client):
    client.get("/login")
    with client.session_transaction() as session:
        return session["csrf_token"]


def register(client, email="student@example.test", name="Student"):
    return client.post(
        "/register",
        data={
            "csrf_token": csrf(client),
            "name": name,
            "email": email,
            "password": "a-long-test-password",
        },
    )


def add_meal(client, **overrides):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    data = {
        "csrf_token": csrf(client),
        "food_key": "rice",
        "grams": "200",
        "meal_type": "Lunch",
        "eaten_on": str(datetime.now(ZoneInfo("Asia/Kolkata")).date()),
        "note": "",
    }
    data.update(overrides)
    return client.post("/meals", data=data)


def chat(client, question):
    return client.post(
        "/api/chat", json={"question": question}, headers={"X-CSRF-Token": csrf(client)}
    )
