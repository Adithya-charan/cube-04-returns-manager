import pytest
from src.engine import DecisionEngine
from src.vision import VisionResult, VisionObservation, EvidenceState
from src.models import Verdict, AmazonCondition, Disposition

def test_engine_identity():
    engine = DecisionEngine()
    
    # Test valid
    res_valid = VisionResult(observations=[
        VisionObservation(object_name="sku_label", observation_type="text", state=EvidenceState.OBSERVED, confidence=0.95, evidence_desc="SKU-1 visible on label", image_reference="label.jpg")
    ], model_name="", model_version="", provider="", latency_ms=0)
    
    chk_valid = engine.verify_identity("sku-1", res_valid)
    assert chk_valid.verdict == Verdict.PASS

    # QR authentication supports identity but cannot replace visual SKU evidence.
    qr_only = VisionResult(observations=[], model_name="", model_version="", provider="", latency_ms=0)
    chk_qr_only = engine.verify_identity("sku-1", qr_only, "AUTHENTICATED")
    assert chk_qr_only.verdict == Verdict.UNCERTAIN

    # Test conflict
    res_conflict = VisionResult(observations=[
        VisionObservation(object_name="product", observation_type="identity", state=EvidenceState.OBSERVED, evidence_desc="Wrong item.", image_reference="")
    ], model_name="", model_version="", provider="", latency_ms=0)
    chk_conflict = engine.verify_identity("sku-1", res_conflict)
    assert chk_conflict.verdict == Verdict.FAIL

    unrelated_observation = VisionResult(observations=[
        VisionObservation(object_name="cable", observation_type="completeness", state=EvidenceState.OBSERVED, confidence=0.99, evidence_desc="Expected SKU-1 is listed on the order", image_reference="accessories.jpg")
    ], model_name="", model_version="", provider="", latency_ms=0)
    assert engine.verify_identity("sku-1", unrelated_observation).verdict == Verdict.UNCERTAIN

    unreadable_label = VisionResult(observations=[
        VisionObservation(object_name="sku_label", observation_type="text", state=EvidenceState.UNCERTAIN, confidence=0.4, evidence_desc="SKU-1 expected but label is blurry and unreadable", image_reference="label.jpg")
    ], model_name="", model_version="", provider="", latency_ms=0)
    assert engine.verify_identity("sku-1", unreadable_label).verdict == Verdict.UNCERTAIN

    asin_label = VisionResult(observations=[
        VisionObservation(object_name="model_label", observation_type="text", state=EvidenceState.OBSERVED, confidence=0.93, evidence_desc="Legible label text: B0MODEL123", image_reference="back-label.jpg")
    ], model_name="", model_version="", provider="", latency_ms=0)
    assert engine.verify_identity("SKU-UNKNOWN", asin_label, expected_identifiers=["B0MODEL123"]).verdict == Verdict.PASS

def test_engine_completeness():
    engine = DecisionEngine()
    
    # Missing explicit
    res = VisionResult(observations=[
        VisionObservation(object_name="cable", observation_type="completeness", state=EvidenceState.MISSING, confidence=0.95, evidence_desc="Cable compartment is clearly visible and empty", image_reference="accessories.jpg")
    ], model_name="", model_version="", provider="", latency_ms=0)
    chk = engine.verify_completeness(["cable"], res)
    assert chk.verdict == Verdict.FAIL
    assert "cable" in chk.detail.lower()
    assert "accessories.jpg" in chk.evidence_refs

    not_visible = VisionResult(observations=[
        VisionObservation(object_name="cable", observation_type="completeness", state=EvidenceState.NOT_OBSERVED, evidence_desc="Cable is outside the camera frame", image_reference="front.jpg")
    ], model_name="", model_version="", provider="", latency_ms=0)
    assert engine.verify_completeness(["cable"], not_visible).verdict == Verdict.UNCERTAIN

    low_confidence = VisionResult(observations=[
        VisionObservation(object_name="cable", observation_type="completeness", state=EvidenceState.OBSERVED, confidence=0.42, evidence_desc="Cable-like object is partially visible", image_reference="accessories.jpg")
    ], model_name="", model_version="", provider="", latency_ms=0)
    assert engine.verify_completeness(["cable"], low_confidence).verdict == Verdict.UNCERTAIN

def test_engine_disposition():
    engine = DecisionEngine()
    from src.models import InspectionCheck
    
    id_pass = InspectionCheck(check_key="id", verdict=Verdict.PASS)
    comp_pass = InspectionCheck(check_key="comp", verdict=Verdict.PASS)
    
    # NEW condition should restock
    disp = engine.compute_disposition(id_pass, comp_pass, AmazonCondition.NEW)
    assert disp == Disposition.restock

    # Uncertain triggers pending
    comp_unc = InspectionCheck(check_key="comp", verdict=Verdict.UNCERTAIN)
    disp2 = engine.compute_disposition(id_pass, comp_unc, AmazonCondition.NEW)
    assert disp2 == Disposition.pending_review

    # Unknown condition rules must not fall through to a sale disposition.
    disp_unknown_condition = engine.compute_disposition(id_pass, comp_pass, None)
    assert disp_unknown_condition == Disposition.pending_review


def test_engine_condition_requires_classifiable_visual_evidence():
    engine = DecisionEngine()
    no_observations = VisionResult(observations=[], model_name="", model_version="", provider="", latency_ms=0)

    check, condition = engine.verify_condition("factory_sealed", no_observations)
    assert check.verdict == Verdict.UNCERTAIN
    assert condition is None

    visual_evidence = VisionResult(observations=[
        VisionObservation(
            object_name="signs_of_use",
            observation_type="condition",
            state=EvidenceState.OBSERVED,
            confidence=0.9,
            evidence_desc="Light surface wear is visible on the lower edge",
            image_reference="condition-closeup.jpg",
        )
    ], model_name="", model_version="", provider="", latency_ms=0)
    check, condition = engine.verify_condition("", visual_evidence)
    assert check.verdict == Verdict.PASS
    assert condition == AmazonCondition.USED_VERY_GOOD
    assert check.evidence_refs == ["condition-closeup.jpg"]
