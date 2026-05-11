from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_recommendations_api():
    response = client.post(
        "/api/v1/recommendations/generate",
        json={
            "profile": {"taxpayer_name": "Priya Shah", "has_medical_insurance": True},
            "salary": {"gross_salary": "1200000"},
            "ais": {"interest_income": "25000", "tds_tcs": "80000"},
            "form26as": {"salary_tds": "90000"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["taxpayer_name"] == "Priya Shah"
    assert "regime_optimization" in body
    assert "consultation_summary" in body

