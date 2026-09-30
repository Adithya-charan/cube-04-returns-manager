import json
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Float, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.declarative import declarative_base

from .models import EvidenceState, InspectionStatus, Verdict, Disposition, AmazonCondition

Base = declarative_base()

class DbReturnRecord(Base):
    __tablename__ = 'returns'

    record_id = Column(String, primary_key=True, index=True)
    unit_id = Column(String, index=True, nullable=False)
    organization_id = Column(String, index=True, nullable=False)
    status = Column(SQLEnum(InspectionStatus), default=InspectionStatus.received, nullable=False)
    correlation_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("DbProductReference", back_populates="return_record", uselist=False, cascade="all, delete-orphan")
    order = relationship("DbOrderReference", back_populates="return_record", uselist=False, cascade="all, delete-orphan")
    evidence = relationship("DbEvidenceItem", back_populates="return_record", cascade="all, delete-orphan")
    checks = relationship("DbInspectionCheck", back_populates="return_record", cascade="all, delete-orphan")
    overrides = relationship("DbHumanOverride", back_populates="return_record", cascade="all, delete-orphan")
    decision = relationship("DbDecisionRecord", back_populates="return_record", uselist=False, cascade="all, delete-orphan")

class DbProductReference(Base):
    __tablename__ = 'products'
    id = Column(String, primary_key=True) # use record_id
    record_id = Column(String, ForeignKey('returns.record_id'))
    ordered_sku = Column(String, nullable=False)
    ordered_asin = Column(String, nullable=False)
    expected_parts = Column(JSON, nullable=False, default=list)

    return_record = relationship("DbReturnRecord", back_populates="product")

class DbOrderReference(Base):
    __tablename__ = 'orders'
    id = Column(String, primary_key=True) # use record_id
    record_id = Column(String, ForeignKey('returns.record_id'))
    order_id = Column(String, nullable=False, index=True)
    organization_id = Column(String, nullable=False)

    return_record = relationship("DbReturnRecord", back_populates="order")

class DbEvidenceItem(Base):
    __tablename__ = 'evidence'
    evidence_id = Column(String, primary_key=True)
    record_id = Column(String, ForeignKey('returns.record_id'))
    media_ref = Column(String, nullable=False)
    captured_at = Column(DateTime(timezone=True), nullable=False)
    content_hash = Column(String, nullable=True)

    return_record = relationship("DbReturnRecord", back_populates="evidence")

class DbInspectionCheck(Base):
    __tablename__ = 'checks'
    id = Column(String, primary_key=True) # combination of record_id and check_key or UUID
    record_id = Column(String, ForeignKey('returns.record_id'))
    check_key = Column(String, nullable=False)
    verdict = Column(SQLEnum(Verdict), nullable=False)
    evidence_refs = Column(JSON, default=list)
    confidence = Column(Float, nullable=True)
    detail = Column(String, nullable=True)
    model_version = Column(String, nullable=True)
    latency_ms = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)

    return_record = relationship("DbReturnRecord", back_populates="checks")

class DbHumanOverride(Base):
    __tablename__ = 'overrides'
    override_id = Column(String, primary_key=True)
    record_id = Column(String, ForeignKey('returns.record_id'))
    original_verdict = Column(String, nullable=False)
    new_verdict = Column(String, nullable=False)
    operator_id = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)

    return_record = relationship("DbReturnRecord", back_populates="overrides")

class DbDecisionRecord(Base):
    __tablename__ = 'decisions'
    record_id = Column(String, ForeignKey('returns.record_id'), primary_key=True)
    outcome = Column(SQLEnum(Disposition), nullable=False)
    content_hash = Column(String, nullable=True)

    return_record = relationship("DbReturnRecord", back_populates="decision")

class DbMedia(Base):
    __tablename__ = 'media'
    media_id = Column(String, primary_key=True)
    organization_id = Column(String, nullable=False, index=True)
    record_id = Column(String, index=True)
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    checksum = Column(String, nullable=False)
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    storage_ref = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)

class DbProductAuthentication(Base):
    __tablename__ = 'product_auth'
    id = Column(String, primary_key=True)
    product_id = Column(String, nullable=False, index=True)
    qr_identifier = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False, default="REGISTERED")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class DbPackageAuthentication(Base):
    __tablename__ = 'package_auth'
    id = Column(String, primary_key=True)
    package_id = Column(String, nullable=False, index=True)
    qr_identifier = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False, default="REGISTERED")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class DbProductPackageBinding(Base):
    __tablename__ = 'product_package_binding'
    id = Column(String, primary_key=True)
    product_id = Column(String, nullable=False, index=True)
    package_id = Column(String, nullable=False, index=True)
    bound_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    status = Column(String, nullable=False, default="VALID")

class DbAuthenticationEvent(Base):
    __tablename__ = 'auth_events'
    id = Column(String, primary_key=True)
    product_id = Column(String, nullable=True)
    package_id = Column(String, nullable=True)
    operator_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    result = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    details = Column(String, nullable=True)
