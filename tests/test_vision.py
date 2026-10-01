import pytest
from src.vision import MockVisionProvider, EvidenceState

def test_mock_vision_provider_success():
    provider = MockVisionProvider(delay_ms=0)
    res = provider.inspect(["img1.jpg"], ["usb_cable", "manual"])
    
    assert res.error is None
    assert res.provider == "mock"
    
    parts_observed = [obs.object_name for obs in res.observations if obs.state == EvidenceState.OBSERVED]
    assert "usb_cable" in parts_observed
    assert "manual" in parts_observed
    assert res.latency_ms >= 0

def test_mock_vision_provider_error():
    provider = MockVisionProvider(forced_error=True, delay_ms=0)
    res = provider.inspect(["img1.jpg"], ["usb_cable"])
    
    assert res.error == "Mock Vision Provider timeout/error"
    assert len(res.observations) == 0


def test_yolo_provider_handles_empty_image_set():
    from src.vision_yolo import YOLODetectionProvider

    provider = YOLODetectionProvider()
    provider._load_model = lambda: pytest.fail("YOLO should not load without images")

    assert provider.detect([], []) == []
