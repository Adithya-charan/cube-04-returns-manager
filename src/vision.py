from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field
import time

from .models import EvidenceState

class VisionObservation(BaseModel):
    observation_type: str = Field(default="generic", description="Category: identity, completeness, condition, damage, text")
    object_name: str = Field(description="The generic name of the component/defect expected")
    state: EvidenceState
    confidence: Optional[float] = None
    evidence_desc: str = Field(description="Reasoning generated based on the image")
    image_reference: str
    bbox: Optional[List[float]] = Field(default=None, description="Bounding box [x1, y1, x2, y2] if applicable")
    
class VisionResult(BaseModel):
    observations: List[VisionObservation]
    model_name: str
    model_version: str
    provider: str
    latency_ms: int
    error: Optional[str] = None

class VisionProvider(ABC):
    @abstractmethod
    def inspect(
        self,
        images: List[str],
        expected_parts: List[str],
        condition_guidance: Optional[str] = None,
        identity_guidance: Optional[str] = None,
        scenario: Optional[str] = None,
    ) -> VisionResult:
        """
        Takes image references and structural expected parts. 
        Returns purely observational states without forming a final rule disposition.
        """
        pass

class MockVisionProvider(VisionProvider):
    def __init__(self, forced_error: bool = False, delay_ms: int = 10):
        self.forced_error = forced_error
        self.delay_ms = delay_ms

    def inspect(
        self,
        images: List[str],
        expected_parts: List[str],
        condition_guidance: Optional[str] = None,
        identity_guidance: Optional[str] = None,
        scenario: Optional[str] = None,
    ) -> VisionResult:
        start_time = time.time()
        time.sleep(self.delay_ms / 1000.0)
        
        if self.forced_error:
            return VisionResult(
                observations=[],
                model_name="mock-vision-provider",
                model_version="1.0",
                provider="mock",
                latency_ms=int((time.time() - start_time) * 1000),
                error="Mock Vision Provider timeout/error"
            )

        guidance_str = f"{scenario or ''} {condition_guidance or ''} {identity_guidance or ''}".lower()
        
        if "scenario_2" in guidance_str or "wrong_product" in guidance_str or "wrong" in guidance_str:
            scen = "SCENARIO_2"
        elif "scenario_3" in guidance_str or "missing_accessory" in guidance_str or "missing" in guidance_str:
            scen = "SCENARIO_3"
        elif "scenario_4" in guidance_str or "uncertain_product" in guidance_str or "uncertain" in guidance_str or "unknown" in guidance_str or "untrusted" in guidance_str:
            scen = "SCENARIO_4"
        elif "scenario_5" in guidance_str or "damaged_product" in guidance_str or "damaged" in guidance_str:
            scen = "SCENARIO_5"
        else:
            scen = "SCENARIO_1"


        observations = []
        img_ref = images[0] if images else "mock_photo.jpg"

        if scen == "SCENARIO_1":
            observations.append(VisionObservation(
                observation_type="identity",
                object_name="product_label",
                state=EvidenceState.OBSERVED,
                confidence=0.95,
                evidence_desc=f"Visible product label matches expected SKU in identity guidance: {identity_guidance or 'SKU-SPEAKER-500'}",
                image_reference=img_ref
            ))
            parts = expected_parts if expected_parts else ["Charging Cable", "Manual", "Power Adapter"]
            for part in parts:
                observations.append(VisionObservation(
                    observation_type="completeness",
                    object_name=part,
                    state=EvidenceState.OBSERVED,
                    confidence=0.94,
                    evidence_desc=f"Detected {part} in retail packaging compartment",
                    image_reference=img_ref
                ))
            observations.append(VisionObservation(
                observation_type="condition",
                object_name="factory_sealed",
                state=EvidenceState.OBSERVED,
                confidence=0.92,
                evidence_desc="Factory sealed box with intact security tamper seal",
                image_reference=img_ref
            ))

        elif scen == "SCENARIO_2":
            observations.append(VisionObservation(
                observation_type="identity",
                object_name="product_label",
                state=EvidenceState.OBSERVED,
                confidence=0.92,
                evidence_desc="Wrong item: Visible product label shows different product SKU-UNKNOWN-999 which does not match expected SKU",
                image_reference=img_ref
            ))
            parts = expected_parts if expected_parts else ["Charging Cable"]
            for part in parts:
                observations.append(VisionObservation(
                    observation_type="completeness",
                    object_name=part,
                    state=EvidenceState.UNCERTAIN,
                    confidence=0.5,
                    evidence_desc=f"Cannot verify {part} for mismatched product item",
                    image_reference=img_ref
                ))
            observations.append(VisionObservation(
                observation_type="condition",
                object_name="signs_of_use",
                state=EvidenceState.OBSERVED,
                confidence=0.85,
                evidence_desc="Item returned in generic non-OEM container",
                image_reference=img_ref
            ))

        elif scen == "SCENARIO_3":
            observations.append(VisionObservation(
                observation_type="identity",
                object_name="product_label",
                state=EvidenceState.OBSERVED,
                confidence=0.94,
                evidence_desc=f"Visible product label matches expected SKU in identity guidance: {identity_guidance or 'SKU-SPEAKER-500'}",
                image_reference=img_ref
            ))
            missing_part = "USB Cable"
            observations.append(VisionObservation(
                observation_type="completeness",
                object_name=missing_part,
                state=EvidenceState.MISSING,
                confidence=0.90,
                evidence_desc=f"{missing_part} compartment is empty; cable is missing",
                image_reference=img_ref
            ))
            parts = expected_parts if expected_parts else ["Manual", "Power Adapter"]
            for part in parts:
                if part.lower() != missing_part.lower():
                    observations.append(VisionObservation(
                        observation_type="completeness",
                        object_name=part,
                        state=EvidenceState.OBSERVED,
                        confidence=0.91,
                        evidence_desc=f"Detected {part} present",
                        image_reference=img_ref
                    ))
            observations.append(VisionObservation(
                observation_type="condition",
                object_name="used_good",
                state=EvidenceState.OBSERVED,
                confidence=0.88,
                evidence_desc="Minor visible signs of use on casing",
                image_reference=img_ref
            ))

        elif scen == "SCENARIO_4":
            observations.append(VisionObservation(
                observation_type="identity",
                object_name="product_label",
                state=EvidenceState.UNCERTAIN,
                confidence=0.45,
                evidence_desc="Product label is unreadable, torn, and blurry; SKU cannot be established",
                image_reference=img_ref
            ))
            parts = expected_parts if expected_parts else ["Charging Cable", "Manual"]
            for part in parts:
                observations.append(VisionObservation(
                    observation_type="completeness",
                    object_name=part,
                    state=EvidenceState.UNCERTAIN,
                    confidence=0.48,
                    evidence_desc=f"Uncertain if {part} is genuine OEM",
                    image_reference=img_ref
                ))
            observations.append(VisionObservation(
                observation_type="condition",
                object_name="signs_of_use",
                state=EvidenceState.UNCERTAIN,
                confidence=0.50,
                evidence_desc="Lighting glare obscures surface texture",
                image_reference=img_ref
            ))

        elif scen == "SCENARIO_5":
            observations.append(VisionObservation(
                observation_type="identity",
                object_name="product_label",
                state=EvidenceState.OBSERVED,
                confidence=0.95,
                evidence_desc=f"Visible product label matches expected SKU in identity guidance: {identity_guidance or 'SKU-SPEAKER-500'}",
                image_reference=img_ref
            ))
            parts = expected_parts if expected_parts else ["Charging Cable", "Manual"]
            for part in parts:
                observations.append(VisionObservation(
                    observation_type="completeness",
                    object_name=part,
                    state=EvidenceState.OBSERVED,
                    confidence=0.92,
                    evidence_desc=f"Detected {part} present",
                    image_reference=img_ref
                ))
            observations.append(VisionObservation(
                observation_type="condition",
                object_name="damaged",
                state=EvidenceState.OBSERVED,
                confidence=0.93,
                evidence_desc="Severe impact damage, cracked chassis and broken internal components observed",
                image_reference=img_ref
            ))

        return VisionResult(
            observations=observations,
            model_name="mock-vision-provider",
            model_version="1.0",
            provider="mock",
            latency_ms=int((time.time() - start_time) * 1000)
        )

