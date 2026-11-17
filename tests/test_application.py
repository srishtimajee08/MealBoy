import io
from datetime import date

import pytest
from PIL import Image

from mealboy.db import get_db
from mealboy.retrieval import question_period
from tests.conftest import add_meal, chat, csrf, register


def test_authentication_and_csrf(client):
    assert client.get("/").status_code == 302
    assert client.post("/register", data={}).status_code == 400
    assert register(client).status_code == 302
    assert client.get("/").status_code == 200
    assert client.post("/logout", data={"csrf_token": csrf(client)}).status_code == 302
    assert (
        client.post(
            "/api/chat", json={"question": "my meals"}, headers={"X-CSRF-Token": csrf(client)}
        ).status_code
        == 401
    )


def test_password_is_hashed_and_login_works(app, client):
    register(client)
    with app.app_context():
        stored = get_db().execute("SELECT password_hash FROM users").fetchone()[0]
        assert "a-long-test-password" not in stored
    client.post("/logout", data={"csrf_token": csrf(client)})
    response = client.post(
        "/login",
        data={
            "csrf_token": csrf(client),
            "email": "student@example.test",
            "password": "a-long-test-password",
        },
    )
    assert response.status_code == 302


def test_meal_totals_are_computed_server_side(app, client):
    register(client)
    assert add_meal(client, calories="1", user_id="999").status_code == 302
    with app.app_context():
        meal = get_db().execute("SELECT * FROM meals").fetchone()
        assert meal["calories"] == 258  # USDA FDC 2708408: 129 kcal / 100 g, portion 200 g.
        assert meal["protein"] == 5.3  # 2.67 g / 100 g, rounded after portion scaling.
        assert meal["user_id"] == 1
        assert meal["entry_method"] == "manual"


@pytest.mark.parametrize("grams", ["nan", "inf", "-2", "0", "5001", "not a number"])
def test_invalid_portions_rejected(client, grams):
    register(client)
    assert add_meal(client, grams=grams).status_code == 400


def test_invalid_food_date_and_type(client):
    register(client)
    assert add_meal(client, food_key="unknown").status_code == 400
    assert add_meal(client, eaten_on="2099-01-01").status_code == 400
    assert add_meal(client, meal_type="arbitrary").status_code == 400


def test_user_isolation_everywhere(app):
    alice, bob = app.test_client(), app.test_client()
    register(alice, "alice@example.test", "Alice")
    add_meal(alice, note="ALICE_PRIVATE_CANARY")
    chat(alice, "What did I log today?")
    register(bob, "bob@example.test", "Bob")
    for route in ["/", "/diary", "/export.csv", "/chat"]:
        assert b"ALICE_PRIVATE_CANARY" not in bob.get(route).data
    response = chat(bob, "ALICE_PRIVATE_CANARY").get_json()
    assert response["sources"] == []
    assert "ALICE_PRIVATE_CANARY" not in response["answer"]
    assert bob.post("/meals/1/delete", data={"csrf_token": csrf(bob)}).status_code == 404
    assert b"ALICE_PRIVATE_CANARY" in alice.get("/diary").data


def test_totals_cover_more_than_retrieval_limit(client):
    register(client)
    for _ in range(9):
        add_meal(client)
    result = chat(client, "How many calories today?").get_json()
    assert "2322 kcal" in result["answer"]  # Nine 200 g portions at 129 kcal / 100 g.
    assert "9 logged meals" in result["answer"]
    assert len(result["sources"]) <= 6
    assert result["sources"][0]["id"] == "period-summary"


def test_profile_retrieval_and_empty_evidence(client):
    register(client)
    result = chat(client, "What is my calorie goal?").get_json()
    assert "2000" in result["answer"]
    assert result["sources"][0]["id"] == "profile"
    assert chat(client, "quantum astrophysics").get_json()["sources"] == []


def test_date_periods():
    today = date(2026, 9, 22)
    assert question_period("this week", today)[:2] == (date(2026, 9, 21), today)
    assert question_period("last week", today)[:2] == (date(2026, 9, 14), date(2026, 9, 20))
    assert question_period("last 7 days", today)[:2] == (date(2026, 9, 16), today)
    with pytest.raises(ValueError):
        question_period("2026-02-30", today)


def test_upload_validation_and_missing_model(client):
    register(client)
    response = client.post(
        "/api/predict",
        data={"csrf_token": csrf(client), "image": (io.BytesIO(b"not-an-image"), "food.jpg")},
    )
    assert response.status_code == 400
    image = io.BytesIO()
    Image.new("RGB", (20, 20), "green").save(image, format="PNG")
    image.seek(0)
    response = client.post(
        "/api/predict", data={"csrf_token": csrf(client), "image": (image, "food.png")}
    )
    assert response.status_code == 503
    assert "predictions" not in response.get_json()


def test_script_notes_are_escaped_and_csv_formulas_neutralized(client):
    register(client)
    add_meal(client, note='<script>alert("x")</script>')
    assert b"<script>alert" not in client.get("/diary").data
    assert b"&lt;script&gt;" in client.get("/diary").data
    add_meal(client, note="=HYPERLINK(1)")
    assert b"'=HYPERLINK(1)" in client.get("/export.csv").data


def test_delete_clears_stale_chat_evidence(client):
    register(client)
    add_meal(client, note="DELETE_ME_CANARY")
    chat(client, "What did I log today?")
    assert b"DELETE_ME_CANARY" in client.get("/chat").data
    client.post("/meals/1/delete", data={"csrf_token": csrf(client)})
    assert b"DELETE_ME_CANARY" not in client.get("/chat").data
    assert "DELETE_ME_CANARY" not in chat(client, "What did I log today?").get_json()["answer"]


def test_local_generator_failure_falls_back_to_evidence(app, client, monkeypatch):
    register(client)
    app.config["CHAT_PROVIDER"] = "ollama"

    def unavailable(*_args):
        raise OSError("Local server offline")

    monkeypatch.setattr("mealboy.chat.generate_with_ollama", unavailable)
    response = chat(client, "What is my calorie goal?").get_json()
    assert response["mode"] == "extractive"
    assert "2000" in response["answer"]
    assert "unavailable" in response["notice"]


def test_pages_render_and_security_headers(client):
    register(client)
    for route in ["/", "/analyze", "/diary", "/chat", "/settings"]:
        response = client.get(route)
        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_rejects_malformed_chat_json(client):
    register(client)
    for payload in [[], {"question": 42}, {"question": "x"}, {"question": "x" * 1001}]:
        assert (
            client.post(
                "/api/chat", json=payload, headers={"X-CSRF-Token": csrf(client)}
            ).status_code
            == 400
        )
