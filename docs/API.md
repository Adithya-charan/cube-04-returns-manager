# Returns Manager: Internal API Boundary

> **Current implementation note (2026-10-01):** The response below is illustrative, not a captured live response. `/inspect` and `/agent` run the configured vision provider and deterministic decision engine; client-provided `operator_disposition` and `qr_auth_result` are not trusted. A server-issued QR verification event can be consumed once by an inspection. QR currently verifies the product/package binding only; it does not establish an order/SKU or tenant binding. The decision hash covers persisted decision/check/evidence references and overrides, while uploaded media has a separate SHA-256 checksum. Neither is a signed or immutable ledger. API `org_id` scoping is not authentication/authorization; do not expose this demo API as production-secure.

## 1. `GET /health`
Returns system service capability including initialization properties.
**Response**: `200 OK`
```json
{
  "status": "ok"
}
```

## 2. `POST /agent`
Endpoint accepting a structured return payload and running the configured vision and decision pipeline. Tenant filtering uses `org_id`, but the current API has no authenticated tenant identity.

**Request Schema Application (RawReturnInput JSON)**
The expected SKU and ASIN are supplied to vision as reference values; only a legible identifier observed in an image can support an identity match.
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
Output follows the project `DecisionRecord` schema and contains checks, evidence references, disposition, review status, and a content hash.
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
      "detail": "No legible matching product identifier was observed.",
      "model_version": "qwen3-vl:8b",
      "latency_ms": null,
      "timestamp": "2026-09-25T01:53:13.123287Z"
    }
    // ... completeness, condition
  ],
  "outcome": "pending_review",
  "overrides": [],
  "status": "pending_review",
  "correlation_id": "a9a3fbeb-2e65-4f40-bcf5-dc5dc8be4ebc",
  "content_hash": "21ec28f4bc4db9ad05e04b4c09d57a3e7428f52ef7174db76de45dcfcd1eef2a"
}
```
**Exception Handling Rules**:
- Standard FastAPI error structures `422 Unprocessable Entity` are supplied upon syntax mismatch.
- Vision-provider errors return no observations and therefore normally produce uncertain checks and `pending_review`; uncaught pipeline exceptions return HTTP 500.

## Evidence and media

- `GET /returns/{record_id}/evidence?org_id={organization_id}` lists persisted evidence metadata and media IDs for a tenant-scoped return. It does not expose storage paths.
- `GET /media/{media_id}?organization_id={organization_id}` returns the image bytes after checking the media row's organization ID.
- `POST /media` validates MIME type, image content, and the 10 MiB upload limit, stores the object checksum, and returns its storage reference for the inspection request.

## QR verification

1. `POST /authentication/bind` creates the demo product/package relationship.
2. `POST /authentication/verify` accepts `product_qr` and `package_qr` form fields and returns a server-generated `qr_auth_result` plus `auth_event_id`.
3. Include `product_qr`, `package_qr`, and `auth_event_id` in the `/inspect` JSON body. The server checks the event and binding and consumes that event once. Client-provided `qr_auth_result` is ignored.

QR records are not yet organization-scoped, and the binding table has no catalogue SKU or order reference. The API currently has no authentication, so this is a local/demo trust boundary, not production authorization.
