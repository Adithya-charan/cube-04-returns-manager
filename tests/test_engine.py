import pytest
from src.engine import DecisionEngine
from src.vision import VisionResult, VisionObservation, EvidenceState
from src.models import Verdict, AmazonCondition, Disposition

def test_engine_identity():
    engine = DecisionEngine()
    
    # Test valid
    res_valid = VisionResult(observations=[
        VisionObservation(object_name="product", state=EvidenceState.OBSERVED, evidence_desc="", image_reference="")
    ], model_name="", model_version="", provider="", latency_ms=0)
    
    chk_valid = engine.verify_identity("sku-1", res_valid)
    assert chk_valid.verdict == Verdict.PASS

    # Test conflict
    res_conflict = VisionResult(observations=[
        VisionObservation(object_name="product", state=EvidenceState.OBSERVED, evidence_desc="Wrong item.", image_reference="")
    ], model_name="", model_version="", provider="", latency_ms=0)
    chk_conflict = engine.verify_identity("sku-1", res_conflict)
    assert chk_conflict.verdict == Verdict.FAIL

def test_engine_completeness():
    engine = DecisionEngine()
    
    # Missing explicit
    res = VisionResult(observations=[
        VisionObservation(object_name="cable", state=EvidenceState.NOT_OBSERVED, evidence_desc="Compartment is visibly empty", image_reference="")
    ], model_name="", model_version="", provider="", latency_ms=0)
    chk = engine.verify_completeness(["cable"], res)
    assert chk.verdict == Verdict.FAIL

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
