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
