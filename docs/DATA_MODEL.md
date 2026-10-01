# Returns Manager: Data Model

> **Implementation note (2026-10-01):** These Pydantic types describe the current contract shape, but not every listed lifecycle entity is persisted or wired into routes. The current content hash covers only `record_id`, `outcome`, override count, and `status`; it does not guarantee full evidence immutability or independent verification.

This document specifies the canonical models strictly utilizing Pydantic in accordance with the official cross-pod schema and `data/returns_sample.csv`. The Phase 2 structures fully separate operational models from AI interpretations while establishing an auditable flow.

## 1. Core Enumerations
- **EvidenceState**: `OBSERVED`, `NOT_OBSERVED`, `UNCERTAIN`, `VERIFIED`
- **InspectionStatus**: `received`, `inspecting`, `pending_review`, `completed`, `failed`
- **Verdict**: `PASS`, `FAIL`, `UNCERTAIN`
- **Disposition**: `restock`, `refurbish`, `liquidate`, `dispose`, `pending_review`
- **AmazonCondition**: `New`, `Used - Like New`, `Used - Very Good`, `Used - Good`, `Used - Acceptable`, `Unacceptable`

## 2. Ingestion Model (RawReturnInput)
Maps identically to `data/returns_sample.csv` payload strings.
- **`record_id`**, **`unit_id`**, **`org_id`**, **`order_id`**, **`ordered_sku`**, **`ordered_asin`**.
- Observational constraints (**`parts_list`**, **`photo_refs`**, **`observed_state`**, **`parts_missing`**).
- Boundary tags (**`operator_id`**, **`operator_disposition`**).

## 3. Structural Operational Blocks (Raw Entities)
Models parsing incoming context prior to AI application:
- **ProductReference**: Anchors tracking of `ordered_sku`, `ordered_asin`, and nested `expected_parts`.
- **OrderReference**: Retains upstream tag `order_id` along bounded `organization_id`.
- **PartsList**: Holds the specific elements of `expected_parts` array, distinct from visually absent `missing_parts_override`.
- **EvidenceItem**: Represents un-processed image references holding `evidence_id`, `media_ref`, and `content_hash`.

## 4. Derived Interpretational Output (AI Logic Output)
Creates strict logical distinction between "what is seen" and "what decisions run".
- **InspectionCheck**: Stores `check_key` mapping (identity, completeness, condition), `verdict` tag, confidence decimals, and specific `evidence_refs` supporting the individual outcome securely locked by a UTC timestamp.
- **InspectionResult**: Binds multiple Checks together under a single `inspection_id`, proposing AI-driven tags like `recommended_condition`, `recommended_disposition`, computing internal bounds of `model_version`, and aggregate `latency_ms`.

## 5. Security & Overrides
- **HumanOverride**: Atomic log entry preserving a full trace from an AI `original_verdict` to a forced `new_verdict`. It tracks `override_id`, `operator_id`, and `reason`.
- **ReviewTask**: Pending queue state container (`task_id`, `record_id`, `status`). Ensures human triage occurs predictably based on UTC tracking.

## 6. Official Cross-Pod Final Output (DecisionRecord)
Final interoperable contract consumed by downstream pods securely locked by hashing limits.
- Contains structural trace limits bounding `organization_id`, `correlation_id` and the `subject` unit tracking identifier.
- Retains visual log boundaries holding raw `images` strings. 
- Aggregates the unified array of `InspectionCheck` models ensuring the `outcome` matches the strict enumeration properties.
- Houses the array of `overrides`.
- Runs `finalize()` to derive a partial SHA-256 content hash from `record_id`, `outcome`, override count, and `status`. This is not a signature and does not cover all evidence fields.

## 7. Lifecycle Container (ReturnRecord)
Wraps the entire logical lifespan across internal boundaries combining:
- Raw references (`ProductReference`, `OrderReference`, `EvidenceItem`)
- Interstitial steps (`InspectionResult`)
- Output decisions (`DecisionRecord`)
Guarantees absolute immutability tracking properties via standard `.created_at` and `.updated_at` variables natively.
