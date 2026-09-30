from typing import List, Optional, Tuple
from .models import (
    InspectionCheck, Verdict, AmazonCondition, Disposition, EvidenceState
)
from .vision import VisionResult, VisionObservation

# The CUBE challenge explicitly requires the published Amazon condition scale
# as the authoritative condition taxonomy (RULES.md:318, ARCHITECTURE.md:27,
# REQUIREMENTS.md:22,65). Do not invent alternative condition scales.

class DecisionEngine:
    def __init__(self):
        # Authoritative condition mapping per CUBE challenge requirements:
        # Maps raw operational observation states to Amazon Condition Scale.
        # Source: Published Amazon Condition Scale (New, Used - Like New,
        # Used - Very Good, Used - Good, Used - Acceptable, Unacceptable).
        self.condition_map = {
            "factory_sealed": AmazonCondition.NEW,
            "opened_unused": AmazonCondition.USED_LIKE_NEW,
            "signs_of_use": AmazonCondition.USED_VERY_GOOD,
            "damaged": AmazonCondition.UNACCEPTABLE,
        }

    def verify_identity(self, expected_sku: str, vision_result: VisionResult, qr_auth_result: Optional[str] = None) -> InspectionCheck:
        """
        Verify product identity against expected SKU and QR Authentication state.
        
        Confidence Policy:
        - Uses MAX confidence across matching observations (any strong evidence supports PASS)
        - CONFLICT ("wrong"/"different" in evidence) → FAIL regardless of confidence
        - No match found → UNCERTAIN (never forces PASS with low confidence)
        """
        confidence_accum = 0.0
        details = []
        is_observed = False
        is_conflict = False

        for obs in vision_result.observations:
            if "wrong" in obs.evidence_desc.lower() or "different" in obs.evidence_desc.lower():
                is_conflict = True
                details.append(obs.evidence_desc)
            if expected_sku.lower() in obs.object_name.lower() or "product" in obs.object_name.lower():
                if obs.state == EvidenceState.OBSERVED:
                    is_observed = True
                    confidence_accum = max(confidence_accum, obs.confidence or 0.0)
                    details.append(obs.evidence_desc)
                    
        # Apply QR Authentication Signals First
        if qr_auth_result == "PRODUCT_PACKAGE_MISMATCH":
            is_conflict = True
            details.insert(0, "QR Authentication: PRODUCT_PACKAGE_MISMATCH (Strong fraud signal)")
        elif qr_auth_result == "AUTHENTICATED":
            is_observed = True
            confidence_accum = max(confidence_accum, 0.95)
            details.insert(0, "QR Authentication: MATCH (Validated)")
        elif qr_auth_result in ["INVALID_CODE", "REPEATED_SCAN", "UNEXPECTED_STATE"]:
            details.insert(0, f"QR Authentication Anomaly: {qr_auth_result}. Routing to review.")
            # We don't automatically call it a conflict (vision might save it), but we force a review
            # by overriding the verdict to UNCERTAIN if it isn't already a FAIL.

        if is_conflict:
            verdict = Verdict.FAIL
        elif is_observed and not is_conflict:
            if qr_auth_result in ["INVALID_CODE", "REPEATED_SCAN", "UNEXPECTED_STATE"]:
                verdict = Verdict.UNCERTAIN
            else:
                verdict = Verdict.PASS
        else:
            verdict = Verdict.UNCERTAIN
            details.append("Insufficient visual identity evidence")

        return InspectionCheck(
            check_key="identity",
            verdict=verdict,
            confidence=confidence_accum,
            detail="; ".join(details) if details else "No evidence",
            model_version=vision_result.model_version,
            latency_ms=vision_result.latency_ms
        )

    def verify_completeness(self, expected_parts: List[str], vision_result: VisionResult) -> InspectionCheck:
        """
        Verify all expected components are present.
        
        Confidence Policy:
        - Starts at 1.0, reduced by MIN confidence of explicitly MISSING parts
        - NOT_OBSERVED without "empty"/"missing" in evidence → UNCERTAIN (not FAIL)
        - Part not found in any observation → UNCERTAIN (not FAIL)
        - All parts OBSERVED → PASS with confidence 1.0
        """
        details = []
        missing_parts = []
        confidence = 1.0

        for part in expected_parts:
            part_observed = False
            for obs in vision_result.observations:
                if part.lower() in obs.object_name.lower():
                    if obs.state == EvidenceState.OBSERVED:
                        part_observed = True
                    elif obs.state == EvidenceState.NOT_OBSERVED:
                        # NOT OBSERVED does NOT automatically mean MISSING unless explicitly confirmed visually empty
                        if "empty" in obs.evidence_desc.lower() or "missing" in obs.evidence_desc.lower():
                            missing_parts.append(part)
                            confidence = min(confidence, obs.confidence or 1.0)
                        else:
                            # It's uncertain if it's there
                            details.append(f"{part} not clearly visible but may be obscured.")

            if not part_observed and part not in missing_parts:
                details.append(f"Cannot firmly establish presence or absence of {part}.")

        if missing_parts:
            verdict = Verdict.FAIL
            details.insert(0, f"Missing: {', '.join(missing_parts)}.")
        elif any("Cannot firmly establish" in d for d in details):
            verdict = Verdict.UNCERTAIN
        else:
            verdict = Verdict.PASS
            details.insert(0, "All parts verified present.")

        return InspectionCheck(
            check_key="completeness",
            verdict=verdict,
            confidence=confidence,
            detail=" ".join(details),
            model_version=vision_result.model_version,
            latency_ms=vision_result.latency_ms
        )

    def verify_condition(self, raw_observed_state: str, vision_result: VisionResult) -> Tuple[InspectionCheck, Optional[AmazonCondition]]:
        # Prefer vision observation over raw state if vision detects damage explicitly
        predicted_condition = self.condition_map.get(raw_observed_state.lower(), None)
        details = [f"Raw state: {raw_observed_state} -> mapped to {predicted_condition}"]
        verdict = Verdict.PASS if predicted_condition else Verdict.UNCERTAIN

        for obs in vision_result.observations:
            if obs.object_name == "signs_of_use" or "damage" in obs.evidence_desc.lower():
                if obs.state == EvidenceState.OBSERVED and "damage" in obs.evidence_desc.lower():
                    predicted_condition = AmazonCondition.UNACCEPTABLE
                    verdict = Verdict.FAIL
                    details.append(f"Vision overriding condition due to damage: {obs.evidence_desc}")

        if verdict == Verdict.UNCERTAIN:
            details.append("Insufficient rules to map condition authoritatively.")

        return InspectionCheck(
            check_key="condition",
            verdict=verdict,
            confidence=1.0,
            detail="; ".join(details),
            model_version=vision_result.model_version,
            latency_ms=vision_result.latency_ms
        ), predicted_condition

    def compute_disposition(self, identity: InspectionCheck, completeness: InspectionCheck, condition: Optional[AmazonCondition]) -> Disposition:
        """
        Deterministic disposition rules per CUBE challenge requirements.
        
        Rules (evaluated in order):
        1. Identity FAIL → DISPOSE (wrong item returned)
        2. Identity UNCERTAIN OR Completeness UNCERTAIN → PENDING_REVIEW
           (insufficient evidence for automated decision)
        3. Completeness FAIL (missing parts):
           - If condition == UNACCEPTABLE → DISPOSE
           - Else → LIQUIDATE (sell as-is with missing parts)
        4. Identity PASS, Completeness PASS (complete item):
           - If condition == NEW or USED_LIKE_NEW → RESTOCK
           - If condition == USED_VERY_GOOD or USED_GOOD → REFURBISH
           - Else (UNACCEPTABLE, USED_ACCEPTABLE, or None) → LIQUIDATE
        
        Qwen provides observations ONLY. This engine makes the final
        business disposition decision deterministically.
        """
        if identity.verdict == Verdict.FAIL:
            return Disposition.dispose
        if identity.verdict == Verdict.UNCERTAIN or completeness.verdict == Verdict.UNCERTAIN:
            return Disposition.pending_review
            
        if completeness.verdict == Verdict.FAIL:
            # Missing parts: dispose if damaged, else liquidate
            if condition == AmazonCondition.UNACCEPTABLE:
                return Disposition.dispose
            return Disposition.liquidate

        # Identity PASS, Completeness PASS
        if condition == AmazonCondition.NEW or condition == AmazonCondition.USED_LIKE_NEW:
            return Disposition.restock
        elif condition == AmazonCondition.USED_VERY_GOOD or condition == AmazonCondition.USED_GOOD:
            return Disposition.refurbish
        else:
            return Disposition.liquidate
