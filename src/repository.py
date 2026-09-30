import uuid
from sqlalchemy.orm import Session
from .models import DecisionRecord, ReturnRecord, RawReturnInput
from .database import (
    DbReturnRecord, DbProductReference, DbOrderReference, DbEvidenceItem,
    DbInspectionCheck, DbHumanOverride, DbDecisionRecord
)

class ReturnRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_decision(self, raw: RawReturnInput, decision: DecisionRecord):
        """Persists the DecisionRecord and structural entities tracing back to the raw input."""
        
        # 1. Base Return Record
        db_return = DbReturnRecord(
            record_id=raw.record_id,
            unit_id=raw.unit_id,
            organization_id=raw.org_id,
            status=decision.status,
            correlation_id=decision.correlation_id
        )
        
        # 2. Product and Order boundaries
        db_product = DbProductReference(
            id=raw.record_id,
            record_id=raw.record_id,
            ordered_sku=raw.ordered_sku,
            ordered_asin=raw.ordered_asin,
            expected_parts=[p.strip() for p in raw.parts_list.split(";") if p.strip()]
        )
        
        db_order = DbOrderReference(
            id=raw.record_id,
            record_id=raw.record_id,
            order_id=raw.order_id,
            organization_id=raw.org_id
        )
        
        # 3. Evidence 
        for img in decision.images:
            ev = DbEvidenceItem(
                evidence_id=str(uuid.uuid4()),
                record_id=raw.record_id,
                media_ref=img,
                captured_at=raw.captured_at
            )
            self.db.add(ev)
            
        # 4. Checks
        for chk in decision.checks:
            db_chk = DbInspectionCheck(
                id=str(uuid.uuid4()),
                record_id=raw.record_id,
                check_key=chk.check_key,
                verdict=chk.verdict,
                evidence_refs=chk.evidence_refs,
                confidence=chk.confidence,
                detail=chk.detail,
                model_version=chk.model_version,
                latency_ms=chk.latency_ms,
                timestamp=chk.timestamp
            )
            self.db.add(db_chk)

        # 5. Overrides
        for ov_idx, ov in enumerate(decision.overrides):
            db_ov = DbHumanOverride(
                override_id=ov.override_id,
                record_id=raw.record_id,
                original_verdict=ov.original_verdict,
                new_verdict=ov.new_verdict,
                operator_id=ov.operator_id,
                reason=ov.reason,
                timestamp=ov.timestamp
            )
            self.db.add(db_ov)

        # 6. Final Decision Reference
        db_decision = DbDecisionRecord(
            record_id=raw.record_id,
            outcome=decision.outcome,
            content_hash=decision.content_hash
        )

        self.db.add_all([db_return, db_product, db_order, db_decision])
        self.db.commit()

    def get_decision_by_record_id(self, record_id: str, org_id: str):
        # Enforce multi-tenancy inherently during queries
        rec = self.db.query(DbReturnRecord).filter(
            DbReturnRecord.record_id == record_id,
            DbReturnRecord.organization_id == org_id
        ).first()
        return rec
