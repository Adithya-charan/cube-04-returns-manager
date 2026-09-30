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
    
class VisionResult(BaseModel):
    observations: List[VisionObservation]
    model_name: str
    model_version: str
    provider: str
    latency_ms: int
    error: Optional[str] = None

class VisionProvider(ABC):
    @abstractmethod
    def inspect(self, images: List[str], expected_parts: List[str], condition_guidance: Optional[str] = None) -> VisionResult:
        """
        Takes image references and structural expected parts. 
        Returns purely observational states without forming a final rule disposition.
        """
        pass

class MockVisionProvider(VisionProvider):
    def __init__(self, forced_error: bool = False, delay_ms: int = 10):
        self.forced_error = forced_error
        self.delay_ms = delay_ms

    def inspect(self, images: List[str], expected_parts: List[str], condition_guidance: Optional[str] = None) -> VisionResult:
        start_time = time.time()
        time.sleep(self.delay_ms / 1000.0)
        
        if self.forced_error:
            return VisionResult(
                observations=[],
                model_name="mock-vision",
                model_version="1.0",
                provider="mock",
                latency_ms=int((time.time() - start_time) * 1000),
                error="Mock Vision Provider timeout/error"
            )

        observations = []
        for img in images:
            # Deterministic mock rule for testing: if 'part x' is expected, we observe it in img1
            for part in expected_parts:
                observations.append(VisionObservation(
                    object_name=part,
                    state=EvidenceState.OBSERVED,
                    confidence=0.95,
                    evidence_desc=f"Detected {part} clearly in mock image",
                    image_reference=img
                ))
            
            # Add a mock condition observation
            observations.append(VisionObservation(
                object_name="signs_of_use",
                state=EvidenceState.NOT_OBSERVED,
                confidence=0.88,
                evidence_desc="No visible scratches or use marks",
                image_reference=img
            ))

        return VisionResult(
            observations=observations,
            model_name="mock-vision",
            model_version="1.0",
            provider="mock",
            latency_ms=int((time.time() - start_time) * 1000)
        )
