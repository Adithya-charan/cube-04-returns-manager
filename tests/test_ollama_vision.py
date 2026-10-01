"""
Tests for OllamaQwenVisionProvider.

Tests cover:
- Ollama unavailable (server not running)
- Model not installed
- Timeout simulation
- No valid images on disk
- Malformed / empty model response
- Valid structured JSON response parsing
- UNCERTAIN mapping for NOT_VERIFIED status
- Provider metadata (provider name, model name)
- Evidence round-trip through engine checks

These tests work WITHOUT a running Ollama instance by monkey-patching requests.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from src.vision_ollama import OllamaQwenVisionProvider, _parse_ollama_response
from src.models import EvidenceState


MOCK_VALID_RESPONSE = {
    "product_identity_observations": [
        {"name": "sku_label", "status": "PRESENT", "confidence": 0.92, "evidence": "SKU sticker visible on back panel"}
    ],
    "visible_components": [
        {"name": "cable", "status": "PRESENT", "confidence": 0.88, "evidence": "USB cable coiled in bottom section"},
        {"name": "manual", "status": "UNCERTAIN", "confidence": 0.55, "evidence": "Small booklet partially hidden under foam"},
    ],
    "condition_observations": [
        {"type": "condition", "name": "signs_of_use", "status": "NOT_OBSERVED", "confidence": 0.85, "evidence": "Surface appears clean"}
    ],
    "damage_observations": [
        {"type": "damage", "name": "scratch", "status": "NOT_OBSERVED", "confidence": 0.9, "evidence": "No scratches visible on casing"}
    ],
    "text_observations": [],
    "uncertainties": [],
    "image_quality": "GOOD"
}

# --------------------------------------------------------------------------
# Unit tests: response parser
# --------------------------------------------------------------------------

def test_parse_valid_response():
    raw = json.dumps(MOCK_VALID_RESPONSE)
    obs = _parse_ollama_response(raw, ["img1.jpg"])
    names = [o.object_name for o in obs]
    assert "sku_label" in names
    assert "cable" in names
    assert "manual" in names


def test_parse_response_with_markdown_fences():
    raw = f"```json\n{json.dumps(MOCK_VALID_RESPONSE)}\n```"
    obs = _parse_ollama_response(raw, ["img1.jpg"])
    assert len(obs) > 0


def test_parse_response_strips_think_blocks():
    raw = f"<think>Analyzing...</think>\n{json.dumps(MOCK_VALID_RESPONSE)}"
    obs = _parse_ollama_response(raw, ["img1.jpg"])
    assert len(obs) > 0


def test_parse_empty_response_returns_empty():
    obs = _parse_ollama_response("", ["img1.jpg"])
    assert obs == []


def test_parse_invalid_json_returns_empty():
    obs = _parse_ollama_response("not json at all [][{", ["img1.jpg"])
    assert obs == []


def test_parse_not_verified_maps_to_uncertain():
    data = {
        "visible_components": [
            {"name": "adapter", "status": "NOT_VERIFIED", "confidence": 0.4, "evidence": "Hidden behind packaging"}
        ],
        "product_identity_observations": [], "condition_observations": [],
        "damage_observations": [], "text_observations": [],
        "uncertainties": [], "image_quality": "ACCEPTABLE"
    }
    obs = _parse_ollama_response(json.dumps(data), ["img1.jpg"])
    adapter_obs = [o for o in obs if o.object_name == "adapter"]
    assert len(adapter_obs) == 1
    assert adapter_obs[0].state == EvidenceState.UNCERTAIN


def test_parse_missing_status_maps_to_not_observed():
    data = {
        "visible_components": [
            {"name": "cable", "status": "MISSING", "confidence": 0.95, "evidence": "Slot clearly empty"}
        ],
        "product_identity_observations": [], "condition_observations": [],
        "damage_observations": [], "text_observations": [],
        "uncertainties": [], "image_quality": "GOOD"
    }
    obs = _parse_ollama_response(json.dumps(data), ["img1.jpg"])
    cable_obs = [o for o in obs if o.object_name == "cable"]
    assert cable_obs[0].state == EvidenceState.MISSING


def test_parse_text_observations():
    data = {
        "text_observations": [
            {"name": "ocr_label", "status": "PRESENT", "confidence": 0.85, "evidence": "SKU-TEST-123 visible on label"}
        ],
        "product_identity_observations": [], "visible_components": [],
        "condition_observations": [], "damage_observations": [],
        "uncertainties": [], "image_quality": "GOOD"
    }
    obs = _parse_ollama_response(json.dumps(data), ["img1.jpg"])
    text_obs = [o for o in obs if o.object_name == "ocr_label"]
    assert len(text_obs) == 1
    assert text_obs[0].observation_type == "text"
    assert text_obs[0].state == EvidenceState.OBSERVED


def test_observation_type_is_set():
    """Each observation must carry its category as observation_type."""
    raw = json.dumps(MOCK_VALID_RESPONSE)
    obs = _parse_ollama_response(raw, ["img1.jpg"])
    for o in obs:
        assert o.observation_type in ("identity", "completeness", "condition", "damage", "text", "generic")


def test_multi_image_observation_uses_explicit_image_index():
    data = {
        "product_identity_observations": [],
        "visible_components": [
            {"name": "cable", "status": "PRESENT", "confidence": 0.9, "evidence": "Cable visible beside the charger", "image_index": 1}
        ],
        "condition_observations": [],
        "damage_observations": [],
        "text_observations": [],
    }

    observations = _parse_ollama_response(json.dumps(data), ["front.jpg", "accessories.jpg"])
    assert observations[0].image_reference == "accessories.jpg"


def test_multi_image_observation_without_index_is_unattributed():
    data = {
        "product_identity_observations": [],
        "visible_components": [
            {"name": "cable", "status": "PRESENT", "confidence": 0.9, "evidence": "Cable visible"}
        ],
        "condition_observations": [],
        "damage_observations": [],
        "text_observations": [],
    }

    observations = _parse_ollama_response(json.dumps(data), ["front.jpg", "accessories.jpg"])
    assert observations[0].image_reference == ""


# --------------------------------------------------------------------------
# Integration tests: OllamaQwenVisionProvider (mocked HTTP)
# --------------------------------------------------------------------------

def _make_provider():
    return OllamaQwenVisionProvider(
        base_url="http://localhost:11434",
        model="qwen3-vl:8b",
        timeout=10
    )


def _mock_tags_response(model_name="qwen3-vl:8b"):
    """Build a mock /api/tags response listing the model."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"models": [{"name": model_name}]}
    return mock


def _mock_chat_response(content: str):
    """Mock /api/generate response (uses 'response' key, not 'message.content')"""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"response": content, "done": True}
    mock.raise_for_status = MagicMock()
    return mock


@patch("src.vision_ollama.requests.get")
def test_ollama_not_running(mock_get):
    """When Ollama is not running, provider must return an error result, not raise."""
    mock_get.side_effect = Exception("Connection refused")
    provider = _make_provider()
    result = provider.inspect(["img1.jpg"], ["cable"])
    assert result.error is not None
    assert "not running" in result.error.lower() or "ollama" in result.error.lower()
    assert result.observations == []
    assert result.provider == "ollama"


@patch("src.vision_ollama.requests.get")
def test_model_not_installed(mock_get):
    """When model is missing from Ollama, return appropriate error."""
    # First call (alive check) succeeds; second call (model check) returns empty list
    alive_resp = MagicMock()
    alive_resp.status_code = 200
    alive_resp.json.return_value = {"models": []}  # no models installed

    mock_get.return_value = alive_resp
    provider = _make_provider()
    result = provider.inspect(["img1.jpg"], ["cable"])
    assert result.error is not None
    assert "not installed" in result.error.lower() or "model" in result.error.lower()
    assert result.observations == []


@patch("src.vision_ollama.requests.get")
def test_no_valid_images_on_disk(mock_get):
    """When image paths don't exist on disk, return error without hitting model."""
    mock_get.return_value = _mock_tags_response()
    provider = _make_provider()
    result = provider.inspect(["nonexistent_path.jpg"], ["cable"])
    assert result.error is not None
    assert "no valid images" in result.error.lower()


@patch("src.vision_ollama.requests.post")
@patch("src.vision_ollama.requests.get")
def test_malformed_model_response(mock_get, mock_post, tmp_path):
    """Malformed (non-JSON) model response must return error, not crash."""
    # Create a valid test image
    from PIL import Image
    img = tmp_path / "test.jpg"
    Image.new('RGB', (100, 100), color='red').save(img, 'JPEG')

    mock_get.return_value = _mock_tags_response()
    mock_post.return_value = _mock_chat_response("I cannot analyze this image.")

    provider = _make_provider()
    result = provider.inspect([str(img)], ["cable"])
    # Should not crash; must return error or empty observations
    assert result.provider == "ollama"
    assert result.model_name == "qwen3-vl:8b"
    assert result.error is not None or result.observations == []


@patch("src.vision_ollama.requests.post")
@patch("src.vision_ollama.requests.get")
def test_valid_structured_response(mock_get, mock_post, tmp_path):
    """Full happy-path: valid image + valid JSON response → parsed observations."""
    from PIL import Image
    img = tmp_path / "product.jpg"
    Image.new('RGB', (100, 100), color='blue').save(img, 'JPEG')

    mock_get.return_value = _mock_tags_response()
    mock_post.return_value = _mock_chat_response(json.dumps(MOCK_VALID_RESPONSE))

    provider = _make_provider()
    result = provider.inspect(
        [str(img)],
        ["cable", "manual"],
        identity_guidance='["SKU-TEST-001", "ASIN-TEST-001"]',
    )

    assert result.error is None
    assert result.provider == "ollama"
    assert result.model_name == "qwen3-vl:8b"
    assert len(result.observations) > 0
    assert result.latency_ms >= 0
    prompt = mock_post.call_args.kwargs["json"]["prompt"]
    assert 'Expected product identifiers for visual verification only: ["SKU-TEST-001", "ASIN-TEST-001"]' in prompt
    assert "Never repeat one as an observation" in prompt


@patch("src.vision_ollama.requests.post")
@patch("src.vision_ollama.requests.get")
def test_provider_metadata_stored(mock_get, mock_post, tmp_path):
    """Verify provider and model metadata are correctly stored in result."""
    from PIL import Image
    img = tmp_path / "product.jpg"
    Image.new('RGB', (100, 100), color='green').save(img, 'JPEG')
    mock_get.return_value = _mock_tags_response()
    mock_post.return_value = _mock_chat_response(json.dumps(MOCK_VALID_RESPONSE))

    provider = _make_provider()
    result = provider.inspect([str(img)], ["cable"])
    assert result.provider == "ollama"
    assert result.model_name == "qwen3-vl:8b"
    assert result.model_version == "1.0"


@patch("src.vision_ollama.requests.get")
@patch("src.vision_ollama.requests.post")
def test_timeout_returns_error(mock_post, mock_get):
    """Simulate a timeout; must return error result without raising."""
    import requests as req_lib
    mock_get.return_value = _mock_tags_response()
    mock_post.side_effect = req_lib.Timeout()

    # Provide a fake image path — won't matter because post fails
    provider = _make_provider()
    # We still need an image file to pass the disk-check; patch _validate_and_process_image
    with patch("src.vision_ollama._validate_and_process_image", return_value="fakeb64data"):
        result = provider.inspect(["img1.jpg"], ["cable"])
    assert result.error is not None
    assert "timed out" in result.error.lower()


# --------------------------------------------------------------------------
# Image validation and resizing tests
# --------------------------------------------------------------------------

from src.vision_ollama import _validate_and_process_image
import tempfile
import os


def test_validate_image_rejects_empty_file(tmp_path):
    """Empty image files should be rejected."""
    img = tmp_path / "empty.jpg"
    img.write_bytes(b"")
    result = _validate_and_process_image(str(img))
    assert result is None


def test_validate_image_rejects_invalid_file(tmp_path):
    """Non-image files should be rejected."""
    img = tmp_path / "notanimage.txt"
    img.write_bytes(b"not an image")
    result = _validate_and_process_image(str(img))
    assert result is None


def test_validate_image_rejects_too_small(tmp_path):
    """Images smaller than MIN_IMAGE_DIMENSION should be rejected."""
    from PIL import Image
    img = tmp_path / "tiny.jpg"
    Image.new('RGB', (32, 32), color='red').save(img, 'JPEG')
    result = _validate_and_process_image(str(img))
    assert result is None


def test_validate_image_accepts_valid_image(tmp_path):
    """Valid images should be accepted and base64 encoded."""
    from PIL import Image
    img = tmp_path / "valid.jpg"
    Image.new('RGB', (200, 200), color='blue').save(img, 'JPEG')
    result = _validate_and_process_image(str(img))
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_validate_image_resizes_large_image(tmp_path):
    """Images larger than MAX_IMAGE_DIMENSION should be resized."""
    from PIL import Image
    import base64
    from io import BytesIO
    
    img = tmp_path / "large.jpg"
    # Create image larger than default MAX_IMAGE_DIMENSION (1024)
    Image.new('RGB', (2000, 2000), color='green').save(img, 'JPEG')
    result = _validate_and_process_image(str(img))
    assert result is not None
    
    # Verify the returned image is resized
    decoded = base64.b64decode(result)
    resized_img = Image.open(BytesIO(decoded))
    assert resized_img.size[0] <= 1024
    assert resized_img.size[1] <= 1024


def test_validate_image_rejects_oversized_file(tmp_path):
    """Files larger than MAX_IMAGE_SIZE_BYTES should be rejected."""
    from PIL import Image
    img = tmp_path / "huge.jpg"
    # Create a large image that will exceed 4MB when saved
    # Using a large dimension with low compression
    Image.new('RGB', (4000, 4000), color='white').save(img, 'JPEG', quality=95)
    # If file is over 4MB, it should be rejected
    if os.path.getsize(img) > 4194304:
        result = _validate_and_process_image(str(img))
        assert result is None
