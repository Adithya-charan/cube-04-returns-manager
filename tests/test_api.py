import pytest
from fastapi.testclient import TestClient
from src.main import app

valid_payload = {
    "record_id": "RTN-0003",
    "unit_id": "UNIT-0003",
    "org_id": "org_demo_bravo",
    "order_id": "ORD-DUMMY-50003",
    "ordered_sku": "SKU-PUZZLE-500",
    "ordered_asin": "B0DUMMY729",
    "identity_match": "yes",
    "parts_list": "puzzle pieces;poster",
    "parts_missing": "",
    "observed_state": "signs_of_use",
    "amazon_condition": "",
    "operator_disposition": "liquidate",
    "photo_refs": "fixtures/returns/UNIT-0003_1.jpg;fixtures/returns/UNIT-0003_2.jpg;fixtures/returns/UNIT-0003_3.jpg",
    "operator_id": "op_chen",
    "captured_at": "2026-07-10T15:54:00Z"
}

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_valid_synthetic_record(client):
    response = client.post("/agent", json=valid_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["record_id"] == "RTN-0003"
    assert data["organization_id"] == "org_demo_bravo"
    assert len(data["images"]) == 3
    assert data["outcome"] == "liquidate"
    assert data["content_hash"] is not None
    assert data["correlation_id"] is not None

def test_missing_required_field(client):
    payload = valid_payload.copy()
    del payload["record_id"]
    response = client.post("/agent", json=payload)
    assert response.status_code == 422

def test_invalid_org_isolation(client):
    payload = valid_payload.copy()
    payload["org_id"] = "invalid_org"
    response = client.post("/agent", json=payload)
    assert response.status_code == 422
    assert "Invalid format for org_id" in response.text

def test_uncertain_evidence_state(client):
    payload = valid_payload.copy()
    payload["operator_disposition"] = None
    # Trigger an actual failure/uncertain path by passing a condition we cant deterministically map
    payload["observed_state"] = "unknown_state_mapping"
    response = client.post("/agent", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["outcome"] == "pending_review"
    # Identity & Completeness PASS (due to mock vision), but Condition is UNCERTAIN
    assert any(chk["verdict"] == "UNCERTAIN" for chk in data["checks"])
    assert data["content_hash"] is not None

def test_human_override_preservation(client):
    response = client.post("/agent", json=valid_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["outcome"] == "liquidate"
    assert len(data["overrides"]) == 1
    override = data["overrides"][0]
    assert override["original_verdict"] == "pending_review"
    assert override["new_verdict"] == "liquidate"
    assert override["operator_id"] == "op_chen"
    assert data["status"] == "completed"

def test_invalid_record_values(client):
    payload = valid_payload.copy()
    payload["photo_refs"] = "   ;  "
    response = client.post("/agent", json=payload)
    assert response.status_code == 422
