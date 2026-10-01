import pytest
import io
from fastapi.testclient import TestClient
from src.main import app

def test_media_upload_and_retrieve(client, monkeypatch):
    import src.main as main_module
    from PIL import Image

    stored_media = {}

    def store_media(file_obj, filename, content_type):
        stored_media["content"] = file_obj.read()
        return "test-storage-ref"

    monkeypatch.setattr(main_module.storage_provider, "upload_file", store_media)
    monkeypatch.setattr(
        main_module.storage_provider,
        "get_file_content",
        lambda storage_ref: stored_media.get("content") if storage_ref == "test-storage-ref" else None,
    )
    
    # Create fake image
    img = Image.new('RGB', (100, 100), color = 'red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    
    files = {
        'file': ('test.jpeg', img_byte_arr.getvalue(), 'image/jpeg')
    }
    data = {
        'record_id': 'RTN-999',
        'organization_id': 'org_demo_alpha'
    }
    
    response = client.post("/media", files=files, data=data)
    assert response.status_code == 200
    meta = response.json()
    assert meta["organization_id"] == "org_demo_alpha"
    assert meta["record_id"] == "RTN-999"
    assert meta["width"] == 100
    assert meta["height"] == 100
    
    media_id = meta["media_id"]
    
    # Test valid retrieval
    get_res = client.get(f"/media/{media_id}?organization_id=org_demo_alpha")
    assert get_res.status_code == 200
    assert get_res.headers["content-type"] == "image/jpeg"
    
    # Test cross-tenant forbidden
    bad_res = client.get(f"/media/{media_id}?organization_id=org_demo_bravo")
    assert bad_res.status_code == 403
    
    # Test unsupported mime
    bad_files = {
        'file': ('test.txt', b'hello world', 'text/plain')
    }
    bad_upload = client.post("/media", files=bad_files, data=data)
    assert bad_upload.status_code == 400

def test_media_storage_name_ignores_untrusted_filename(client, monkeypatch):
    from PIL import Image
    import src.main as main_module

    stored = {}

    def capture_upload(file_obj, filename, content_type):
        stored["filename"] = filename
        stored["content_type"] = content_type
        return "test-storage-ref"

    monkeypatch.setattr(main_module.storage_provider, "upload_file", capture_upload)

    img = Image.new("RGB", (100, 100), color="red")
    image_bytes = io.BytesIO()
    img.save(image_bytes, format="JPEG")
    response = client.post(
        "/media",
        files={"file": ("photo.jpg\\..\\..\\outside", image_bytes.getvalue(), "image/jpeg")},
        data={"record_id": "RTN-TRAVERSAL", "organization_id": "org_demo_alpha"},
    )

    assert response.status_code == 200
    assert stored["filename"] == f"{response.json()['media_id']}.jpg"

def test_media_rejects_mismatched_content_type(client):
    from PIL import Image

    image_bytes = io.BytesIO()
    Image.new("RGB", (100, 100), color="red").save(image_bytes, format="PNG")
    response = client.post(
        "/media",
        files={"file": ("photo.jpg", image_bytes.getvalue(), "image/jpeg")},
        data={"record_id": "RTN-MIME-MISMATCH", "organization_id": "org_demo_alpha"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Image content does not match file type"


def test_return_evidence_listing_is_scoped_and_retrievable(client, monkeypatch):
    import src.main as main_module
    from PIL import Image

    image_bytes = io.BytesIO()
    Image.new("RGB", (100, 100), color="blue").save(image_bytes, format="JPEG")
    content = image_bytes.getvalue()
    storage_ref = "test-evidence/RTN-EVIDENCE-LISTING.jpg"
    monkeypatch.setattr(main_module.storage_provider, "upload_file", lambda *_: storage_ref)
    monkeypatch.setattr(main_module.storage_provider, "get_file_content", lambda ref: content if ref == storage_ref else None)

    upload = client.post(
        "/media",
        files={"file": ("photo.jpg", content, "image/jpeg")},
        data={"record_id": "RTN-EVIDENCE-LISTING", "organization_id": "org_demo_alpha"},
    )
    assert upload.status_code == 200
    media_id = upload.json()["media_id"]

    inspection = client.post("/inspect", json={
        "record_id": "RTN-EVIDENCE-LISTING",
        "unit_id": "UNIT-EVIDENCE-LISTING",
        "org_id": "org_demo_alpha",
        "order_id": "ORD-EVIDENCE-LISTING",
        "ordered_sku": "SKU-EVIDENCE-LISTING",
        "ordered_asin": "ASIN-EVIDENCE-LISTING",
        "parts_list": "product",
        "photo_refs": storage_ref,
        "operator_id": "op_evidence_listing",
        "captured_at": "2026-10-01T00:00:00Z",
    })
    assert inspection.status_code == 200
    inspection_data = inspection.json()

    stored_return = client.get(
        "/returns/RTN-EVIDENCE-LISTING",
        params={"org_id": "org_demo_alpha"},
    )
    assert stored_return.status_code == 200
    completeness = next(check for check in stored_return.json()["checks"] if check["check_key"] == "completeness")
    assert storage_ref in completeness["evidence_refs"]
    assert stored_return.json()["content_hash"] == inspection_data["content_hash"]

    evidence = client.get(
        "/returns/RTN-EVIDENCE-LISTING/evidence",
        params={"org_id": "org_demo_alpha"},
    )
    assert evidence.status_code == 200
    assert evidence.json()[0]["media_id"] == media_id

    image = client.get(f"/media/{media_id}", params={"organization_id": "org_demo_alpha"})
    assert image.status_code == 200
    assert image.content == content

    cross_tenant = client.get(
        "/returns/RTN-EVIDENCE-LISTING/evidence",
        params={"org_id": "org_demo_bravo"},
    )
    assert cross_tenant.status_code == 404
