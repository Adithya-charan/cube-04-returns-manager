import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base
from src.repository import ReturnRepository
from src.models import (
    RawReturnInput, DecisionRecord, InspectionStatus, Disposition, 
    InspectionCheck, Verdict, HumanOverride
)
from datetime import datetime, timezone

DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_save_and_retrieve_decision(db):
    repo = ReturnRepository(db)
    
    mock_input = RawReturnInput(
        record_id="RTN-DB-001",
        unit_id="UNIT-DB-001",
        org_id="org_demo_alpha",
        order_id="ORD-001",
        ordered_sku="SKU-1",
        ordered_asin="ASIN-1",
        parts_list="part x",
        photo_refs="ref1;ref2",
        operator_id="op_jane",
        captured_at=datetime.now(timezone.utc)
    )

    decision = DecisionRecord(
        record_id=mock_input.record_id,
        organization_id=mock_input.org_id,
        subject=mock_input.unit_id,
        captured_at=mock_input.captured_at,
        operator_label=mock_input.operator_id,
        images=["ref1", "ref2"],
        checks=[
             InspectionCheck(check_key="identity", verdict=Verdict.PASS)
        ],
        outcome=Disposition.restock,
        status=InspectionStatus.completed,
        correlation_id=str(uuid.uuid4())
    )
    decision.finalize()

    # Save
    repo.save_decision(mock_input, decision)

    # Retrieve 
    retrieved = repo.get_decision_by_record_id("RTN-DB-001", "org_demo_alpha")
    assert retrieved is not None
    assert retrieved.record_id == "RTN-DB-001"
    assert retrieved.status.name == "completed"
    
    # Test Isolation (Should not return if requested using a different org)
    invalid_org = repo.get_decision_by_record_id("RTN-DB-001", "org_demo_bravo")
    assert invalid_org is None

    # Check relations
    assert retrieved.product.ordered_sku == "SKU-1"
    assert len(retrieved.evidence) == 2
    assert len(retrieved.checks) == 1
    assert retrieved.decision.outcome.name == "restock"
