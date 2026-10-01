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
    assert data["outcome"] == "pending_review"
    assert data["overrides"] == []
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

def test_operator_disposition_requires_review_resolution(client):
    payload = valid_payload.copy()
    payload["record_id"] = "RTN-OPERATOR-DISPOSITION"
    payload["operator_disposition"] = "dispose"
    response = client.post("/agent", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["outcome"] == "pending_review"
    assert data["overrides"] == []
    original_hash = data["content_hash"]

    resolved = client.post(
        f"/reviews/{payload['record_id']}/resolve",
        params={
            "new_disposition": "liquidate",
            "operator_id": "op_chen",
            "org_id": payload["org_id"],
            "reason": "Verified during physical review",
        },
    )
    assert resolved.status_code == 200

    stored = client.get(f"/returns/{payload['record_id']}", params={"org_id": payload["org_id"]})
    assert stored.status_code == 200
    result = stored.json()
    assert result["outcome"] == "liquidate"
    assert result["status"] == "completed"
    assert result["content_hash"] != original_hash
    assert result["overrides"][0]["original_verdict"] == "pending_review"
    assert result["overrides"][0]["new_verdict"] == "liquidate"
    assert result["overrides"][0]["reason"] == "Verified during physical review"

@pytest.mark.parametrize("qr_result", ["AUTHENTICATED", "PRODUCT_PACKAGE_MISMATCH"])
def test_client_qr_result_cannot_change_identity(client, qr_result):
    payload = valid_payload.copy()
    payload["record_id"] = f"RTN-UNTRUSTED-QR-{qr_result}"
    payload["operator_disposition"] = None
    payload["qr_auth_result"] = qr_result

    response = client.post("/inspect", json=payload)

    assert response.status_code == 200
    data = response.json()
    identity = next(check for check in data["checks"] if check["check_key"] == "identity")
    assert identity["verdict"] == "UNCERTAIN"
    assert data["outcome"] == "pending_review"

def test_invalid_record_values(client):
    payload = valid_payload.copy()
    payload["photo_refs"] = "   ;  "
    response = client.post("/agent", json=payload)
    assert response.status_code == 422
