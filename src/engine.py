import re
from typing import List, Optional, Tuple
from .models import (
    InspectionCheck, Verdict, AmazonCondition, Disposition, EvidenceState
)
from .vision import VisionResult, VisionObservation

# The CUBE challenge explicitly requires the published Amazon condition scale
# as the authoritative condition taxonomy (RULES.md:318, ARCHITECTURE.md:27,
# REQUIREMENTS.md:22,65). Do not invent alternative condition scales.

class DecisionEngine:
    IDENTITY_PASS_CONFIDENCE = 0.8
    COMPONENT_VERDICT_CONFIDENCE = 0.7

    def __init__(self):
        # Authoritative condition mapping per CUBE challenge requirements:
        # Maps raw operational observation states to Amazon Condition Scale.
        # Source: Published Amazon Condition Scale (New, Used - Like New,
        # Used - Very Good, Used - Good, Used - Acceptable, Unacceptable).
        self.condition_map = {
            "factory_sealed": AmazonCondition.NEW,
            "opened_unused": AmazonCondition.USED_LIKE_NEW,
            "signs_of_use": AmazonCondition.USED_VERY_GOOD,
            "used_good": AmazonCondition.USED_GOOD,
            "used_acceptable": AmazonCondition.USED_ACCEPTABLE,
            "damaged": AmazonCondition.UNACCEPTABLE,
        }

    def verify_identity(
        self,
        expected_sku: str,
        vision_result: VisionResult,
        qr_auth_result: Optional[str] = None,
        expected_identifiers: Optional[List[str]] = None,
    ) -> InspectionCheck:
        """
        Verify product identity against expected SKU and QR Authentication state.
        
        Only a legible positive identifier observation can establish an identity match.
        Visual similarity, accessory observations, and QR alone cannot establish PASS.
        """
        confidence_accum = 0.0
        details = []
        evidence_refs = set()
        has_identifier_match = False
        is_conflict = False
        identifiers = [expected_sku, *(expected_identifiers or [])]
        identifier_patterns = [
            re.compile(rf"(?<![a-z0-9]){re.escape(identifier.casefold())}(?![a-z0-9])")
            for identifier in identifiers if identifier
        ]

        for obs in vision_result.observations:
            if obs.observation_type not in {"identity", "text"}:
                continue

            evidence = f"{obs.object_name} {obs.evidence_desc}"
            evidence_lower = evidence.lower()
            if any(term in evidence_lower for term in ("wrong item", "different product", "identifier mismatch", "does not match")):
                is_conflict = True
                details.append(obs.evidence_desc)
                evidence_refs.add(obs.image_reference)

            match_is_qualified_negative = any(term in evidence_lower for term in ("not legible", "unreadable", "blurry", "not visible", "not present"))
            confidence = obs.confidence or 0.0
            if (
                obs.state == EvidenceState.OBSERVED
                and not match_is_qualified_negative
                and any(pattern.search(evidence_lower) for pattern in identifier_patterns)
                and confidence >= self.IDENTITY_PASS_CONFIDENCE
            ):
                has_identifier_match = True
                confidence_accum = max(confidence_accum, confidence)
                details.append(obs.evidence_desc)
                evidence_refs.add(obs.image_reference)
                    
        # Apply QR Authentication Signals First
        if qr_auth_result == "PRODUCT_PACKAGE_MISMATCH":
            is_conflict = True
            details.insert(0, "QR Authentication: PRODUCT_PACKAGE_MISMATCH (Strong fraud signal)")
        elif qr_auth_result == "AUTHENTICATED":
            details.insert(0, "QR Authentication: MATCH (supporting signal only)")
        elif qr_auth_result in ["INVALID_CODE", "REPEATED_SCAN", "UNEXPECTED_STATE"]:
            details.insert(0, f"QR Authentication Anomaly: {qr_auth_result}. Routing to review.")
            # We don't automatically call it a conflict (vision might save it), but we force a review
            # by overriding the verdict to UNCERTAIN if it isn't already a FAIL.

        if is_conflict:
            verdict = Verdict.FAIL
        elif has_identifier_match and not is_conflict:
            if qr_auth_result in ["INVALID_CODE", "REPEATED_SCAN", "UNEXPECTED_STATE"]:
                verdict = Verdict.UNCERTAIN
            else:
                verdict = Verdict.PASS
        else:
            verdict = Verdict.UNCERTAIN
            details.append("No visual evidence matching the expected SKU")

        return InspectionCheck(
            check_key="identity",
            verdict=verdict,
            evidence_refs=sorted(ref for ref in evidence_refs if ref),
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
        uncertain_parts = []
        evidence_refs = set()
        confidence_scores = []

        for part in expected_parts:
            matching = [
                obs for obs in vision_result.observations
                if part.casefold() in obs.object_name.casefold()
                and obs.observation_type == "completeness"
            ]
            observed = [
                obs for obs in matching
                if obs.state == EvidenceState.OBSERVED
                and (obs.confidence or 0.0) >= self.COMPONENT_VERDICT_CONFIDENCE
            ]
            explicitly_missing = [
                obs for obs in matching
                if obs.state == EvidenceState.MISSING
                and (obs.confidence or 0.0) >= self.COMPONENT_VERDICT_CONFIDENCE
            ]
            low_confidence = [
                obs for obs in matching
                if obs.state in {EvidenceState.OBSERVED, EvidenceState.MISSING}
                and (obs.confidence or 0.0) < self.COMPONENT_VERDICT_CONFIDENCE
            ]

            for obs in matching:
                evidence_refs.add(obs.image_reference)
                if obs.confidence is not None:
                    confidence_scores.append(obs.confidence)

            if observed and explicitly_missing:
                uncertain_parts.append(part)
                details.append(f"{part}: CONFLICTING EVIDENCE across images.")
            elif explicitly_missing:
                missing_parts.append(part)
                details.append(f"{part}: MISSING. {explicitly_missing[0].evidence_desc}")
            elif observed:
                details.append(f"{part}: PRESENT. {observed[0].evidence_desc}")
            elif low_confidence:
                uncertain_parts.append(part)
                details.append(f"{part}: NOT_VERIFIED. Confidence below {self.COMPONENT_VERDICT_CONFIDENCE:.1f}. {low_confidence[0].evidence_desc}")
            else:
                uncertain_parts.append(part)
                reason = matching[0].evidence_desc if matching else "No component observation was returned."
                details.append(f"{part}: NOT_VERIFIED. {reason}")

        if not expected_parts:
            uncertain_parts.append("expected components")
            details.append("No expected components were provided.")

        if uncertain_parts:
            verdict = Verdict.UNCERTAIN
        elif missing_parts:
            verdict = Verdict.FAIL
        else:
            verdict = Verdict.PASS

        if missing_parts:
            details.insert(0, f"Missing components: {', '.join(missing_parts)}.")

        confidence = min(confidence_scores) if confidence_scores else 0.0

        return InspectionCheck(
            check_key="completeness",
            verdict=verdict,
            evidence_refs=sorted(ref for ref in evidence_refs if ref),
            confidence=confidence,
            detail=" ".join(details),
            model_version=vision_result.model_version,
            latency_ms=vision_result.latency_ms
        )

    def verify_condition(self, raw_observed_state: str, vision_result: VisionResult) -> Tuple[InspectionCheck, Optional[AmazonCondition]]:
        visual_observations = [
            obs for obs in vision_result.observations
            if obs.observation_type in {"condition", "damage"}
        ]
        classified = [
            (self.condition_map[obs.object_name.casefold()], obs)
            for obs in visual_observations
            if obs.state == EvidenceState.OBSERVED
            and obs.object_name.casefold() in self.condition_map
            and (obs.confidence or 0.0) >= 0.7
        ]
        raw_condition = self.condition_map.get(raw_observed_state.casefold())
        observed_conditions = {condition for condition, _ in classified}
        has_ambiguous_visual_evidence = any(
            obs.state in {EvidenceState.UNCERTAIN, EvidenceState.NOT_OBSERVED}
            and obs.object_name.casefold() in self.condition_map
            for obs in visual_observations
        )

        predicted_condition = next(iter(observed_conditions)) if len(observed_conditions) == 1 else None
        details = []
        if predicted_condition:
            details.extend(
                f"{obs.object_name} -> {condition.value}: {obs.evidence_desc}"
                for condition, obs in classified
            )
        if raw_condition and predicted_condition and raw_condition != predicted_condition:
            details.append(f"Operator condition note conflicts with visual evidence ({raw_condition.value}).")
            predicted_condition = None

        is_confident = bool(classified) and not has_ambiguous_visual_evidence and len(observed_conditions) == 1
        verdict = Verdict.PASS if is_confident and predicted_condition else Verdict.UNCERTAIN
        if verdict == Verdict.UNCERTAIN:
            details.append("Insufficient or conflicting visual evidence to classify condition.")

        confidence = min((obs.confidence or 0.0) for _, obs in classified) if classified else 0.0

        return InspectionCheck(
            check_key="condition",
            verdict=verdict,
            evidence_refs=sorted({obs.image_reference for obs in visual_observations if obs.image_reference}),
            confidence=confidence,
            detail="; ".join(details),
            model_version=vision_result.model_version,
            latency_ms=vision_result.latency_ms
        ), predicted_condition

    def compute_disposition(self, identity: InspectionCheck, completeness: InspectionCheck, condition: Optional[AmazonCondition]) -> Disposition:
        """
        Deterministic disposition rules per CUBE challenge requirements.
        
        Rules (evaluated in order):
        1. Identity FAIL → DISPOSE (wrong item returned)
        2. Identity UNCERTAIN, Completeness UNCERTAIN, or unknown condition → PENDING_REVIEW
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
        if identity.verdict == Verdict.UNCERTAIN or completeness.verdict == Verdict.UNCERTAIN or condition is None:
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
