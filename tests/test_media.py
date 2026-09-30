import pytest
import io
from fastapi.testclient import TestClient
from src.main import app

def test_media_upload_and_retrieve(client):
    from PIL import Image
    
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
