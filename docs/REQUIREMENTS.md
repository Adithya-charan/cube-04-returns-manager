# Returns Manager - Technical Requirements

## 1. Problem Statement
**Position**: Step 4 of 5 (Customer Return) in the end-to-end operational chain.
**Role**: A Returns Manager agent to assess the condition and disposition of returned parcels.
**Consumer**: The downstream consumer is the Recovery Manager.
**Goal**: In a few seconds, analyze a returned parcel to answer four core questions:
- Is this the item sold? (Identity)
- Is it complete? (Completeness)
- What condition is it in? (Condition)
- What should happen to it next? (Disposition)
The output must be structured, consistent, and evidence-backed.

## 2. Required Inputs & Outputs
**Inputs**:
- Operational data: `unit_id`, `order_id`, `ordered_sku`, `ordered_asin`, expected `parts_list`, `org_id`, etc.
- Visual/Input Evidence: Images (`photo_refs`) and observation input capturing the returned item.

**Outputs (Structured Evidence Record)**:
- **Identity**: Verification against the ordered SKU/ASIN.
- **Completeness**: Evaluated against the expected parts list.
- **Condition**: Graded strictly on the published Amazon condition scale.
- **Disposition**: Recommended next action (`restock`, `refurbish`, `liquidate`, `dispose`, or `pending_review`).
- All decisions must include a verdict (`PASS`, `FAIL`, `UNCERTAIN`), confidence, and supporting detail where applicable.

## 3. Synthetic Data Schema
The `data/returns_sample.csv` provides reference data. Key columns include:
- Identifiers: `record_id`, `unit_id`, `order_id`, `org_id`, `operator_id`
- Order Details: `ordered_sku`, `ordered_asin`, `parts_list`
- Evaluation Details: `identity_match`, `parts_missing`, `observed_state` (raw observation, not a grade), `amazon_condition` (deliberately empty for the agent to fill), `operator_disposition`
- Media: `photo_refs` (placeholder paths - actual images must be created/provided)
- Metadata: `captured_at`

## 4. Official Constraints & Rules
- **Tenancy Isolation**: Organization/client data must remain strictly isolated (using `org_demo_alpha` and `org_demo_bravo` for testing).
- **Batching**: Related reasoning should be batched to optimize model use and minimize latency and cost.
- **Fail Open**: If a failure or timeout occurs, do not drop the record. Preserve info and route to a pending/review state.
- **Authoritative Rules**: Condition and rules must use authoritative external sources, avoiding reliance on LLM memories, synthetic sample values, or invented taxonomies.
- **UNCERTAIN is Valid**: Do not force ambiguous cases to pass/fail. Unreliable evidence should result in `UNCERTAIN` and trigger human review.
- **Overrides are Data**: If an operator disagrees, capture the original verdict, new verdict, and reason.

## 5. Expected Evaluation Methodology
Evaluation forms 25% of the Round 2 score. It requires:
- An unseen/held-out evaluation set of at least **50 unseen units** (for visual checks).
- Independent labeling by at least two humans.
- Measured reporting on:
  - Accuracy and results per critical check (Identity, Completeness, Condition, Disposition).
  - False positives (FP) and false negatives (FN).
  - `UNCERTAIN` / review rate.
  - Important failure modes and latency/cost where applicable.
- The evaluation must include genuinely ambiguous or difficult cases. Unrealistic cherry-picking is forbidden.

## 6. Required Evidence / Decision Record
The agent must produce a structured record complying with the official Returns Manager evidence contract for interoperability. Expected fields:
- `record_id`, `schema_version`, `organization_id`, `client_id`
- `agent`, `subject`, `captured_at`, `operator_label`
- `images`, `checks` (with `check_key`, `verdict`, `confidence`, `detail`, `model_version`, `latency_ms`)
- `outcome`, `overrides`, `status`, `content_hash`

## 7. What the Worked Example Demonstrates
*If available in resources,* the worked example indicates the required standard of system outputs. It highlights that decisions should be completely traceable (Item -> Identity Check -> Completeness -> Condition -> Disposition -> Evidence Record). It establishes an expected quality baseline—do not blindly copy it, but rather ensure the submission meets or exceeds its level of transparency and structure.

## 8. What We Must NOT Assume
- **Do not assume the synthetic data is authoritative**: The `returns_sample.csv` values are dummy data; never treat requirement flags or money amounts as ground truth.
- **Do not invent condition scales**: Must strictly use Amazon's published condition scale.
- **Do not assume images exist in the repo**: The `photo_refs` are placeholders; we must supply or mock appropriate image fixtures for testing.
- **Do not invent cross-pod contracts**: We must use the official evidence contract format given by the organizers, rather than creating bespoke cross-pod negotiation contracts for Round 2.
- **Do not guess secrets boundaries**: Tenant isolation must be mechanically verified. We cannot assume identifiers alone confer privacy.
- **Do not blindly pass/fail**: Do not assume every case can be cleanly resolved—ambiguity means `UNCERTAIN`.
