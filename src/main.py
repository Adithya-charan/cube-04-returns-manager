import os
import uuid
import hashlib
import logging
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime, timezone
from PIL import Image
import io

from .models import (
    RawReturnInput, DecisionRecord, InspectionStatus, Disposition, 
    InspectionCheck, Verdict, HumanOverride, MediaMetadata
)
from .db_config import init_db, get_db
from .repository import ReturnRepository
from .database import (
    DbMedia, DbReturnRecord, DbDecisionRecord, DbHumanOverride,
    DbProductPackageBinding, DbProductAuthentication, DbPackageAuthentication, DbAuthenticationEvent
)
from .vision import MockVisionProvider
from .vision_ollama import OllamaQwenVisionProvider
from .engine import DecisionEngine
from .storage import ObjectStorageProvider
from .vision_yolo import YOLODetectionProvider

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("returns_manager")

app = FastAPI(title="Returns Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # LOCAL DEVELOPMENT ONLY - allows LAN phone access
    # PRODUCTION: Replace with specific frontend origin(s):
    # allow_origins=["https://your-frontend-domain.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_DIR = "fixtures/returns"
os.makedirs(STORAGE_DIR, exist_ok=True)

# Production provider: local Ollama + qwen3-vl:8b.
# No external API key required.
# Override in tests via app.dependency_overrides or pytest fixture.
vision_provider = OllamaQwenVisionProvider()
yolo_provider = YOLODetectionProvider()
storage_provider = ObjectStorageProvider()

engine = DecisionEngine()

@app.on_event("startup")
def startup_event():
    init_db()
    logger.info("Returns Manager API started")

@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}

@app.post("/agent", response_model=DecisionRecord)
@app.post("/inspect", response_model=DecisionRecord)
def process_return_pipeline(return_input: RawReturnInput, db: Session = Depends(get_db)):
    """Orchestrates Return lookup -> Vision -> Engine -> Persistence -> Human Override bounds"""
    correlation_id = str(uuid.uuid4())
    logger.info(
        "pipeline_start",
        extra={
            "record_id": return_input.record_id,
            "correlation_id": correlation_id,
            "org_id": return_input.org_id,
            "unit_id": return_input.unit_id,
            "sku": return_input.ordered_sku,
            "parts_count": len([p.strip() for p in return_input.parts_list.split(";") if p.strip()]),
            "image_count": len([p.strip() for p in return_input.photo_refs.split(";") if p.strip()]),
        }
    )
    try:
        photos = [p.strip() for p in return_input.photo_refs.split(";") if p.strip()]
        expected_parts = [p.strip() for p in return_input.parts_list.split(";") if p.strip()]
        
        # Load images for YOLO (from Object Storage or local)
        pil_images = []
        valid_photos = []
        for photo_ref in photos:
            bytes_data = storage_provider.get_file_content(photo_ref)
            if bytes_data:
                pil_images.append(Image.open(io.BytesIO(bytes_data)))
                valid_photos.append(photo_ref)
                
        yolo_observations = yolo_provider.detect(pil_images, valid_photos)
        
        vision_result = vision_provider.inspect(images=photos, expected_parts=expected_parts, condition_guidance=return_input.observed_state)
        vision_result.observations.extend(yolo_observations)
        
        logger.info(
            "vision_complete",
            extra={
                "record_id": return_input.record_id,
                "correlation_id": correlation_id,
                "provider": vision_result.provider,
                "model": vision_result.model_name,
                "latency_ms": vision_result.latency_ms,
                "observations_count": len(vision_result.observations),
                "error": vision_result.error,
            }
        )
        
        identity_check = engine.verify_identity(return_input.ordered_sku, vision_result, return_input.qr_auth_result)
        completeness_check = engine.verify_completeness(expected_parts, vision_result)
        condition_check, condition_val = engine.verify_condition(return_input.observed_state or "", vision_result)
        
        checks = [identity_check, completeness_check, condition_check]
        
        AI_outcome = engine.compute_disposition(identity_check, completeness_check, condition_val)
        
        logger.info(
            "disposition_computed",
            extra={
                "record_id": return_input.record_id,
                "correlation_id": correlation_id,
                "identity_verdict": identity_check.verdict.value,
                "completeness_verdict": completeness_check.verdict.value,
                "condition_verdict": condition_check.verdict.value,
                "condition": condition_val.value if condition_val else None,
                "disposition": AI_outcome.value,
            }
        )
        
        status = InspectionStatus.pending_review if AI_outcome == Disposition.pending_review else InspectionStatus.completed
        
        decision = DecisionRecord(
            record_id=return_input.record_id,
            organization_id=return_input.org_id,
            subject=return_input.unit_id,
            captured_at=return_input.captured_at,
            operator_label=return_input.operator_id,
            images=photos,
            checks=checks,
            outcome=AI_outcome,
            status=status,
            correlation_id=correlation_id
        )

        if return_input.operator_disposition:
            decision.overrides.append(
                HumanOverride(
                    original_verdict=AI_outcome.value,
                    new_verdict=return_input.operator_disposition,
                    operator_id=return_input.operator_id,
                    reason="Human Disposition override from operator input"
                )
            )
            try:
                decision.outcome = Disposition(return_input.operator_disposition)
                decision.status = InspectionStatus.completed 
            except ValueError:
                pass
                
        decision.finalize()

        repo = ReturnRepository(db)
        existing = repo.get_decision_by_record_id(return_input.record_id, return_input.org_id)
        if not existing:
            repo.save_decision(return_input, decision)
        
        logger.info(
            "pipeline_complete",
            extra={
                "record_id": return_input.record_id,
                "correlation_id": correlation_id,
                "final_disposition": decision.outcome.value,
                "status": decision.status.value,
                "content_hash": decision.content_hash,
            }
        )
        
        return decision
    except Exception as e:
        logger.error(
            "pipeline_error",
            extra={
                "record_id": return_input.record_id,
                "correlation_id": correlation_id,
                "error": str(e),
            }
        )
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Pipeline exception: {str(e)}")

@app.get("/returns/{record_id}", response_model=DecisionRecord)
def execute_cross_pod_export(record_id: str, org_id: str, db: Session = Depends(get_db)):
    repo = ReturnRepository(db)
    rec = repo.get_decision_by_record_id(record_id, org_id)
    if not rec or not rec.decision:
        raise HTTPException(status_code=404, detail="Evidentiary structure not found")
        
    dec = DecisionRecord(
        record_id=rec.record_id,
        organization_id=rec.organization_id,
        subject=rec.unit_id,
        captured_at=rec.created_at,
        operator_label="db_load",
        images=[ev.media_ref for ev in rec.evidence],
        checks=[
            InspectionCheck(
                check_key=c.check_key,
                verdict=c.verdict,
                confidence=c.confidence,
                detail=c.detail,
                model_version=c.model_version
            ) for c in rec.checks
        ],
        outcome=rec.decision.outcome,
        overrides=[
            HumanOverride(
                override_id=o.override_id,
                original_verdict=o.original_verdict,
                new_verdict=o.new_verdict,
                operator_id=o.operator_id,
                reason=o.reason,
                timestamp=o.timestamp
            ) for o in rec.overrides
        ],
        status=rec.status,
        content_hash=rec.decision.content_hash,
        correlation_id=rec.correlation_id
    )
    return dec

@app.get("/reviews")
def get_reviews_list(org_id: str, db: Session = Depends(get_db)):
    recs = db.query(DbReturnRecord).filter(
        DbReturnRecord.organization_id == org_id,
        DbReturnRecord.status == InspectionStatus.pending_review
    ).all()
    return [{"record_id": r.record_id, "status": r.status.value, "created_at": r.created_at} for r in recs]

@app.post("/reviews/{record_id}/resolve")
def resolve_review(record_id: str, new_disposition: str, operator_id: str, org_id: str, reason: str, db: Session = Depends(get_db)):
    repo = ReturnRepository(db)
    rec = repo.get_decision_by_record_id(record_id, org_id)
    if not rec or not rec.decision:
        raise HTTPException(status_code=404, detail="Return not found for review")
    if rec.status != InspectionStatus.pending_review:
        raise HTTPException(status_code=400, detail="Return is not pending review")

    try:
        new_disp_enum = Disposition(new_disposition)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid disposition")

    ov = DbHumanOverride(
        override_id=str(uuid.uuid4()),
        record_id=record_id,
        original_verdict=rec.decision.outcome.value,
        new_verdict=new_disp_enum.value,
        operator_id=operator_id,
        reason=reason,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(ov)
    
    rec.decision.outcome = new_disp_enum
    rec.status = InspectionStatus.completed 
    db.commit()
    return {"status": "resolved", "new_outcome": new_disposition}

ALLOWED_EXTENSIONS = {"jpeg", "jpg", "png", "webp"}
ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp"}

@app.post("/media", response_model=MediaMetadata)
async def upload_media(
    file: UploadFile = File(...),
    record_id: str = Form(...),
    organization_id: str = Form(...),
    db: Session = Depends(get_db)
):
    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail="Invalid file type")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
        img = Image.open(io.BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image content")

    width, height = img.size
    checksum = hashlib.sha256(content).hexdigest()
    media_id = str(uuid.uuid4())
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "jpg"
    safe_filename = f"{media_id}.{ext}"

    storage_ref = storage_provider.upload_file(io.BytesIO(content), safe_filename, file.content_type)

    meta = MediaMetadata(
        media_id=media_id,
        record_id=record_id,
        organization_id=organization_id,
        filename=file.filename,
        mime_type=file.content_type,
        checksum=checksum,
        width=width,
        height=height,
        storage_ref=storage_ref,
        timestamp=datetime.now(timezone.utc)
    )

    db_media = DbMedia(
        media_id=media_id,
        organization_id=organization_id,
        record_id=record_id,
        filename=file.filename,
        mime_type=file.content_type,
        checksum=checksum,
        width=width,
        height=height,
        storage_ref=storage_ref,
        timestamp=meta.timestamp
    )
    db.add(db_media)
    db.commit()

    return meta

@app.get("/media/{media_id}")
def get_media(media_id: str, organization_id: str, db: Session = Depends(get_db)):
    db_media = db.query(DbMedia).filter(DbMedia.media_id == media_id).first()
    if not db_media:
        raise HTTPException(status_code=404, detail="Media not found")
    if db_media.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Cross-tenant access forbidden")
    data = storage_provider.get_file_content(db_media.storage_ref)
    if not data:
        raise HTTPException(status_code=404, detail="Media content not found in storage")
    return Response(content=data, media_type=db_media.mime_type)

@app.post("/authentication/bind")
def bind_product_package(
    product_qr: str = Form(...), 
    package_qr: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Operator explicitly binds a product to a package to establish their trusted relationship.
    """
    bind = DbProductPackageBinding(
        id=str(uuid.uuid4()),
        product_id=product_qr,  # Using QR as ID directly in demo for simplicity
        package_id=package_qr,
        status="VALID"
    )
    db.add(bind)
    db.commit()
    return {"status": "bound"}

@app.post("/authentication/verify")
def verify_authentication(
    product_qr: str = Form(...),
    package_qr: str = Form(...),
    operator_id: str = Form("demo_auth_operator"),
    db: Session = Depends(get_db)
):
    """
    Verify if the scanned product QR matches the scanned package QR.
    Records history for repeated-scan detection.
    """
    # 1. Simple Binding Check
    binding = db.query(DbProductPackageBinding).filter(
        DbProductPackageBinding.product_id == product_qr,
        DbProductPackageBinding.package_id == package_qr,
        DbProductPackageBinding.status == "VALID"
    ).first()
    
    # 2. Replay / Repeated Scan Check (basic demo logic)
    history_count = db.query(DbAuthenticationEvent).filter(
        DbAuthenticationEvent.product_id == product_qr,
        DbAuthenticationEvent.event_type == "verify"
    ).count()

    if history_count >= 1:
        result = "REPEATED_SCAN"
        msg = "Anomaly: This product has already been verified in a previous session."
    elif binding:
        result = "AUTHENTICATED"
        msg = "Product and Package bindings match."
    else:
        # Is product bound to something else?
        other_binding = db.query(DbProductPackageBinding).filter(
            DbProductPackageBinding.product_id == product_qr
        ).first()
        if other_binding:
            result = "PRODUCT_PACKAGE_MISMATCH"
            msg = "Product is bound to a different package!"
        else:
            result = "INVALID_CODE"
            msg = "No binding found for these codes."

    event = DbAuthenticationEvent(
        id=str(uuid.uuid4()),
        product_id=product_qr,
        package_id=package_qr,
        operator_id=operator_id,
        event_type="verify",
        result=result,
        details=msg
    )
    db.add(event)
    db.commit()

    return {
        "status": "success",
        "qr_auth_result": result,
        "message": msg
    }
