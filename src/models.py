import hashlib
import json
import uuid
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone

class EvidenceState(str, Enum):
    OBSERVED = "OBSERVED"
    MISSING = "MISSING"
    NOT_OBSERVED = "NOT_OBSERVED"
    UNCERTAIN = "UNCERTAIN"
    VERIFIED = "VERIFIED"

class InspectionStatus(str, Enum):
    received = "received"
    inspecting = "inspecting"
    pending_review = "pending_review"
    completed = "completed"
    failed = "failed"

class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNCERTAIN = "UNCERTAIN"

class Disposition(str, Enum):
    restock = "restock"
    refurbish = "refurbish"
    liquidate = "liquidate"
    dispose = "dispose"
    pending_review = "pending_review"

class AmazonCondition(str, Enum):
    NEW = "New"
    USED_LIKE_NEW = "Used - Like New"
    USED_VERY_GOOD = "Used - Very Good"
    USED_GOOD = "Used - Good"
    USED_ACCEPTABLE = "Used - Acceptable"
    UNACCEPTABLE = "Unacceptable"

class QRAuthResult(str, Enum):
    AUTHENTICATED = "AUTHENTICATED"
    PRODUCT_PACKAGE_MISMATCH = "PRODUCT_PACKAGE_MISMATCH"
    INVALID_CODE = "INVALID_CODE"
    REPEATED_SCAN = "REPEATED_SCAN"
    UNEXPECTED_STATE = "UNEXPECTED_STATE"
    PENDING_REVIEW = "PENDING_REVIEW"

class AuthenticationEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: Optional[str] = None
    package_id: Optional[str] = None
    operator_id: str
    event_type: str
    result: QRAuthResult
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Optional[str] = None


# 1. ProductReference
class ProductReference(BaseModel):
    ordered_sku: str
    ordered_asin: str
    expected_parts: List[str] = Field(default_factory=list)

# 2. OrderReference
class OrderReference(BaseModel):
    order_id: str
    organization_id: str

# 3. PartsList
class PartsList(BaseModel):
    expected_parts: List[str]
    missing_parts_override: Optional[List[str]] = None

# 4. EvidenceItem
class EvidenceItem(BaseModel):
    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    media_ref: str
    captured_at: datetime
    content_hash: Optional[str] = None

# 5. InspectionCheck
class InspectionCheck(BaseModel):
    check_key: str = Field(..., description="E.g., identity, completeness, condition")
    verdict: Verdict
    evidence_refs: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    detail: Optional[str] = None
    model_version: Optional[str] = None
    latency_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# 6. InspectionResult (Internal AI evaluation boundary output)
class InspectionResult(BaseModel):
    inspection_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    checks: List[InspectionCheck]
    recommended_condition: Optional[AmazonCondition] = None
    recommended_disposition: Optional[Disposition] = None
    model_version: Optional[str] = None
    latency_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# 7. HumanOverride
class HumanOverride(BaseModel):
    override_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_verdict: str
    new_verdict: str
    operator_id: str
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# 8. DecisionRecord (The official cross-pod Evidence Record contract)
class DecisionRecord(BaseModel):
    record_id: str
    schema_version: str = "1.0"
    organization_id: str
    client_id: Optional[str] = None
    agent: str = "returns-manager"
    subject: str
    captured_at: datetime
    operator_label: str
    images: List[str]
    checks: List[InspectionCheck]
    outcome: Disposition
    overrides: List[HumanOverride] = Field(default_factory=list)
    status: InspectionStatus
    correlation_id: Optional[str] = None
    content_hash: Optional[str] = None

    def finalize(self):
        """Hash the decision and its persisted evidence for tamper detection."""
        def normalized_timestamp(value: datetime) -> str:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            else:
                value = value.astimezone(timezone.utc)
            return value.isoformat()

        data_to_hash = {
            "record_id": self.record_id,
            "organization_id": self.organization_id,
            "subject": self.subject,
            "images": sorted(self.images),
            "checks": sorted(
                [
                    {
                        "check_key": check.check_key,
                        "verdict": check.verdict.value,
                        "evidence_refs": sorted(check.evidence_refs),
                        "confidence": check.confidence,
                        "detail": check.detail,
                        "model_version": check.model_version,
                        "latency_ms": check.latency_ms,
                        "timestamp": normalized_timestamp(check.timestamp),
                    }
                    for check in self.checks
                ],
                key=lambda check: (check["check_key"], check["detail"] or ""),
            ),
            "outcome": self.outcome.value,
            "overrides": sorted(
                [
                    {
                        "override_id": override.override_id,
                        "original_verdict": override.original_verdict,
                        "new_verdict": override.new_verdict,
                        "operator_id": override.operator_id,
                        "reason": override.reason,
                        "timestamp": normalized_timestamp(override.timestamp),
                    }
                    for override in self.overrides
                ],
                key=lambda override: override["override_id"],
            ),
            "status": self.status.value
        }
        canonical_data = json.dumps(data_to_hash, sort_keys=True, separators=(",", ":"))
        self.content_hash = hashlib.sha256(canonical_data.encode()).hexdigest()

# 9. ReturnRecord (The core overarching bounded context entity)
class ReturnRecord(BaseModel):
    record_id: str
    unit_id: str
    organization_id: str
    product_ref: ProductReference
    order_ref: OrderReference
    evidence: List[EvidenceItem] = Field(default_factory=list)
    inspection_result: Optional[InspectionResult] = None
    decision: Optional[DecisionRecord] = None
    status: InspectionStatus = InspectionStatus.received
    correlation_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# 10. ReviewTask
class ReviewTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    record_id: str
    organization_id: str
    status: str = "open" # open, resolved, rejected
    reason: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

# Ingestion DTO (Data Transfer Object matching raw CSV for parsing)
class RawReturnInput(BaseModel):
    record_id: str = Field(...)
    unit_id: str = Field(...)
    org_id: str = Field(...)
    order_id: str = Field(...)
    ordered_sku: str
    ordered_asin: str
    identity_match: Optional[str] = None
    parts_list: str
    parts_missing: Optional[str] = None
    observed_state: Optional[str] = None
    amazon_condition: Optional[str] = None
    operator_disposition: Optional[str] = None
    photo_refs: str
    operator_id: str
    captured_at: datetime
    product_qr: Optional[str] = None
    package_qr: Optional[str] = None
    auth_event_id: Optional[str] = None
    qr_auth_result: Optional[str] = None
    scenario: Optional[str] = None

    @field_validator('record_id')
    @classmethod
    def validate_record_id(cls, v):
        if not v or not v.strip():
            raise ValueError("record_id must not be empty")
        return v

    @field_validator('org_id')
    @classmethod
    def validate_org_id(cls, v):
        if not v or not v.strip():
            raise ValueError("org_id must not be empty for tenant isolation")
        if not v.startswith("org_"):
            raise ValueError("Invalid format for org_id")
        return v
    
    @field_validator('ordered_sku', 'ordered_asin')
    @classmethod
    def validate_identity(cls, v, info):
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} must be populated to check product identity")
        return v

    @field_validator('parts_list')
    @classmethod
    def validate_parts_list(cls, v):
        if not v or not v.strip():
            raise ValueError("parts_list cannot be empty")
        return v

    @field_validator('photo_refs')
    @classmethod
    def validate_photos(cls, v):
        if not v or not v.strip():
            raise ValueError("photos/evidence references cannot be empty")
        parsed = [p.strip() for p in v.split(";") if p.strip()]
        if not parsed:
            raise ValueError("Parsed photo references cannot be empty")
        return v

    @field_validator('operator_id')
    @classmethod
    def validate_operator(cls, v):
        if not v or not v.strip():
            raise ValueError("operator information must be populated")
        return v

class MediaMetadata(BaseModel):
    media_id: str
    record_id: str
    organization_id: str
    filename: str
    mime_type: str
    checksum: str
    width: Optional[int]
    height: Optional[int]
    storage_ref: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
