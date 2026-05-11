import json

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_parse_json_upload():
    payload = {
        "transactions": [
            {"information_category": "Interest income", "amount": "11000", "source_name": "Bank"},
            {"information_category": "Capital gains", "amount": "70000", "source_name": "Broker"},
        ]
    }
    response = client.post(
        "/api/v1/ais/parse",
        data={"assessment_year": "2026-27"},
        files={"file": ("ais.json", json.dumps(payload), "application/json")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["interest_income"] == "11000"
    assert body["summary"]["capital_gains"] == "70000"

