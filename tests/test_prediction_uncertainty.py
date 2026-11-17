import io

import pytest
from PIL import Image

from tests.conftest import csrf, register


@pytest.mark.parametrize("score,uncertain", [(0.35, True), (0.85, False)])
def test_prediction_uncertainty_and_nutrition_support(app, client, score, uncertain):
    class StubRecognizer:
        confidence_threshold = 0.8

        def predict(self, image):
            return [{"label": "beignets", "confidence": score}]

    register(client)
    app.extensions["recognizer"] = StubRecognizer()
    image = io.BytesIO()
    Image.new("RGB", (16, 16), "white").save(image, format="PNG")
    image.seek(0)
    response = client.post(
        "/api/predict", data={"csrf_token": csrf(client), "image": (image, "meal.png")}
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["uncertain"] is uncertain
    assert payload["needs_confirmation"] is True
    assert payload["predictions"][0]["supported"] is False
