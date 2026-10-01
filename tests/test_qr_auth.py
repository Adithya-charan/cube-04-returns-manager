def test_qr_binding_and_verification(client):
    # 1. Bind
    res = client.post("/authentication/bind", data={
        "product_qr": "PRD-123",
        "package_qr": "PKG-123"
    })
    assert res.status_code == 200
    assert res.json() == {"status": "bound"}

    # 2. Verify successfully
    res = client.post("/authentication/verify", data={
        "product_qr": "PRD-123",
        "package_qr": "PKG-123",
        "operator_id": "test_op"
    })
    assert res.status_code == 200
    assert res.json()["qr_auth_result"] == "AUTHENTICATED"

    # 3. Repeated scan
    res = client.post("/authentication/verify", data={
        "product_qr": "PRD-123",
        "package_qr": "PKG-123",
        "operator_id": "test_op"
    })
    assert res.status_code == 200
    assert res.json()["qr_auth_result"] == "REPEATED_SCAN"

def test_qr_mismatch(client):
    client.post("/authentication/bind", data={
        "product_qr": "PRD-999",
        "package_qr": "PKG-999"
    })
    
    # Try mismatch
    res = client.post("/authentication/verify", data={
        "product_qr": "PRD-999",
        "package_qr": "PKG-UNKNOWN",
        "operator_id": "test_op"
    })
    assert res.status_code == 200
    assert res.json()["qr_auth_result"] == "PRODUCT_PACKAGE_MISMATCH"

def test_qr_invalid(client):
    res = client.post("/authentication/verify", data={
        "product_qr": "PRD-INVALID",
        "package_qr": "PKG-INVALID",
        "operator_id": "test_op"
    })
    assert res.status_code == 200
    assert res.json()["qr_auth_result"] == "INVALID_CODE"


def test_server_generated_qr_result_is_used_in_identity_decision(client):
    bind = client.post("/authentication/bind", data={
        "product_qr": "PRD-SERVER-IDENTITY",
        "package_qr": "PKG-SERVER-IDENTITY"
    })
    assert bind.status_code == 200

    payload = {
        "record_id": "RTN-SERVER-QR-IDENTITY",
        "unit_id": "UNIT-SERVER-QR",
        "org_id": "org_demo_alpha",
        "order_id": "ORD-SERVER-QR",
        "ordered_sku": "SKU-SERVER-QR",
        "ordered_asin": "ASIN-SERVER-QR",
        "parts_list": "product",
        "photo_refs": "fixtures/returns/UNIT-0003_1.jpg;fixtures/returns/UNIT-0003_2.jpg;fixtures/returns/UNIT-0003_3.jpg",
        "operator_id": "op_server_qr",
        "captured_at": "2026-07-10T15:54:00Z",
        "product_qr": "PRD-SERVER-IDENTITY",
        "package_qr": "PKG-SERVER-IDENTITY"
    }

    response = client.post("/inspect", json=payload)
    assert response.status_code == 200
    identity = next(item for item in response.json()["checks"] if item["check_key"] == "identity")
    assert "QR Authentication: MATCH" in identity["detail"]


def test_verified_qr_event_is_bound_to_one_inspection(client, monkeypatch):
    import src.main as main_module

    monkeypatch.setattr(main_module.yolo_provider, "detect", lambda *_: [])
    product_qr = "PRD-ONE-USE-EVENT"
    package_qr = "PKG-ONE-USE-EVENT"
    client.post("/authentication/bind", data={"product_qr": product_qr, "package_qr": package_qr})
    verification = client.post("/authentication/verify", data={
        "product_qr": product_qr,
        "package_qr": package_qr,
        "operator_id": "op_one_use",
    })
    assert verification.status_code == 200
    event_id = verification.json()["auth_event_id"]

    payload = {
        "record_id": "RTN-QR-ONE-USE-1",
        "unit_id": "UNIT-QR-ONE-USE-1",
        "org_id": "org_demo_alpha",
        "order_id": "ORD-QR-ONE-USE-1",
        "ordered_sku": "SKU-QR-ONE-USE-1",
        "ordered_asin": "ASIN-QR-ONE-USE-1",
        "parts_list": "product",
        "photo_refs": "fixtures/returns/UNIT-0003_1.jpg",
        "operator_id": "op_one_use",
        "captured_at": "2026-10-01T00:00:00Z",
        "product_qr": product_qr,
        "package_qr": package_qr,
        "auth_event_id": event_id,
        "qr_auth_result": "PRODUCT_PACKAGE_MISMATCH",
    }

    first = client.post("/inspect", json=payload)
    assert first.status_code == 200
    first_identity = next(item for item in first.json()["checks"] if item["check_key"] == "identity")
    assert "QR Authentication: MATCH" in first_identity["detail"]

    replay_payload = {**payload, "record_id": "RTN-QR-ONE-USE-2", "unit_id": "UNIT-QR-ONE-USE-2"}
    replay = client.post("/inspect", json=replay_payload)
    assert replay.status_code == 200
    replay_identity = next(item for item in replay.json()["checks"] if item["check_key"] == "identity")
    assert "REPEATED_SCAN" in replay_identity["detail"]
