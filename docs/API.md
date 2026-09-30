# Returns Manager: Internal API Boundary

## 1. `GET /health`
Returns system service capability including initialization properties.
**Response**: `200 OK`
```json
{
  "status": "ok"
}
```

## 2. `POST /agent`
Endpoint utilizing JSON structure for standard batch ingestion triggering Vision mapping processes. Validates completely against `returns_sample.csv` syntax context. 
Requires full tenant isolation enforcement embedded on payload delivery via headers/`org_id` metadata.

**Request Schema Application (RawReturnInput JSON)**
```json
{
    "record_id": "RTN-0003",
    "unit_id": "UNIT-0003",
    "org_id": "org_demo_bravo",
    "order_id": "ORD-DUMMY-50003",
    "ordered_sku": "SKU-PUZZLE-500",
    "ordered_asin": "B0DUMMY729",
    "identity_match": "yes",
    "parts_list": "puzzle pieces;poster",
    "parts_missing": "",
    "observed_state": "signs_of_use",
    "amazon_condition": "",
    "operator_disposition": "liquidate",
    "photo_refs": "fixtures/returns/UNIT-0003_1.jpg;fixtures/returns/UNIT-0003_2.jpg",
    "operator_id": "op_chen",
    "captured_at": "2026-07-10T15:54:00Z"
}
```

**Standard Response Schema (`DecisionRecord`, 200 OK)**
Output complies tightly with the cross-pod `EvidenceRecord` paradigm ensuring logical separation of derived fields (now generating correlation tags and immutable content bounds).
```json
{
  "record_id": "RTN-0003",
  "schema_version": "1.0",
  "organization_id": "org_demo_bravo",
  "client_id": null,
  "agent": "returns-manager",
  "subject": "UNIT-0003",
  "captured_at": "2026-07-10T15:54:00Z",
  "operator_label": "op_chen",
  "images": [
    "fixtures/returns/UNIT-0003_1.jpg",
    "fixtures/returns/UNIT-0003_2.jpg"
  ],
  "checks": [
    {
      "check_key": "identity",
      "verdict": "UNCERTAIN",
      "evidence_refs": [],
      "confidence": 0.0,
      "detail": "AI inspection not yet implemented",
      "model_version": null,
      "latency_ms": null,
      "timestamp": "2026-09-25T01:53:13.123287Z"
    }
    // ... completeness, condition
  ],
  "outcome": "liquidate",
  "overrides": [
    {
      "override_id": "848bd1ef-7bf2-41ba-ac4e-ecbc656c3826",
      "original_verdict": "pending_review",
      "new_verdict": "liquidate",
      "operator_id": "op_chen",
      "reason": "Human Disposition override from operator input",
      "timestamp": "2026-09-25T01:53:13.123287Z"
    }
  ],
  "status": "completed",
  "correlation_id": "a9a3fbeb-2e65-4f40-bcf5-dc5dc8be4ebc",
  "content_hash": "21ec28f4bc4db9ad05e04b4c09d57a3e7428f52ef7174db76de45dcfcd1eef2a"
}
```
**Exception Handling Rules**:
- Standard FastAPI error structures `422 Unprocessable Entity` are supplied upon syntax mismatch.
- Hard data breaks fail open returning `200` enclosing soft internal bounds matching `UNCERTAIN` for individual `checks` components directing `status` -> `pending_review`.
