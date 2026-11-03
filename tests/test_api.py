from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    assert client.get("/health").json()["status"] == "ok"

def test_inventory_has_items():
    response = client.get("/inventory")
    assert response.status_code == 200
    assert response.json()["count"] >= 1

def test_availability_rejects_unknown_item():
    response = client.get("/availability", params={"item_id": "missing", "start": "2026-11-10", "end": "2026-11-11"})
    assert response.status_code == 404

def test_quote_calculates_fee():
    response = client.post("/quotes", json={"item_id": "beach-chair-01", "quantity": 2, "days": 3})
    assert response.status_code == 200
    assert response.json()["total"] == 75.6

def test_late_return_requires_approval():
    response = client.post("/agent/recommend", json={"scenario": "late_return", "booking_id": "BK-204", "hours_late": 5})
    body = response.json()
    assert response.status_code == 200
    assert body["requires_human_approval"] is True
    assert body["execution"] == "not_performed"
