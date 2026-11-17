import pytest

from mealboy.body_metrics import calculate
from mealboy.db import get_db
from tests.conftest import chat, csrf, register


def test_published_equation_and_bmi():
    male = calculate(30, 175, 70, "male", "moderate")
    assert male["bmi"] == 22.9
    assert male["bmr"] == 1649
    assert male["tdee"] == 2556
    assert male["bmi_category"] == "Healthy weight"
    female = calculate(30, 175, 70, "female", "sedentary")
    assert female["bmr"] == 1483
    assert female["tdee"] == 1779
    assert calculate(30, 200, 100, "male", "light")["bmi_category"] == "Overweight"


@pytest.mark.parametrize(
    "age,height,weight", [(19, 175, 70), (30, "nan", 70), (30, 175, "inf"), (30, 0, 70)]
)
def test_invalid_measurements(age, height, weight):
    with pytest.raises(ValueError):
        calculate(age, height, weight, "male", "moderate")


def test_measurements_are_private_and_do_not_change_goal(app, client):
    register(client)
    response = client.post(
        "/settings/measurements",
        data={
            "csrf_token": csrf(client),
            "age": "30",
            "height_cm": "175",
            "weight_kg": "70",
            "formula_sex": "male",
            "activity": "moderate",
            "user_id": "999",
        },
    )
    assert response.status_code == 302
    assert b"2556 kcal/day" in client.get("/settings").data
    assert "2556" in chat(client, "What is my TDEE?").get_json()["answer"]
    with app.app_context():
        assert get_db().execute("SELECT calorie_goal FROM users").fetchone()[0] == 2000
    other = app.test_client()
    register(other, "other@example.test", "Other")
    assert b"2556 kcal/day" not in other.get("/settings").data
    assert "2556" not in chat(other, "What is my TDEE?").get_json()["answer"]
    client.post("/settings/measurements", data={"csrf_token": csrf(client), "action": "clear"})
    assert b"2556 kcal/day" not in client.get("/settings").data
