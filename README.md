<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f172a,50:1e1b4b,100:0c4a6e&height=200&section=header&text=CUBE%20Returns%20Manager&fontSize=42&fontColor=f8fafc&animation=fadeIn&fontAlignY=38&desc=CUBE%20Build-A-Thon%202026%20%C2%B7%20Track%2004%20%E2%80%94%20Returns%20Manager&descAlignY=58&descSize=16&descColor=cbd5e1" alt="CUBE Returns Manager header" width="100%"/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&duration=3000&pause=1000&color=38BDF8&center=true&vCenter=true&width=720&height=45&lines=AI+observes;Rules+decide;Humans+resolve+uncertainty" alt="AI observes. Rules decide. Humans resolve uncertainty."/>

</div>

# CUBE Returns Manager

**CUBE Build-A-Thon 2026 · Track 04 — Returns Manager**

CUBE Returns Manager is a local-first prototype for inspecting returned products. FastAPI accepts product references and uploaded images, a vision model (Qwen3-VL:8B through Ollama) is asked for structured visual observations, and a deterministic Python engine turns those observations into identity, completeness, and condition checks and a disposition. Ambiguous results are routed to a human-review endpoint, and every decision is stored with its evidence.

> **Status:** demo, not a production-secure multi-tenant service. See [Current Implementation Status](#current-implementation-status) for exactly what is and is not verified.

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Workflow](#workflow)
- [Core Inspection Checks](#core-inspection-checks)
- [AI Architecture](#ai-architecture)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Backend](#backend)
- [Frontend](#frontend)
- [Data and Evidence](#data-and-evidence)
- [Human-in-the-Loop](#human-in-the-loop)
- [API / Workflow Example](#api--workflow-example)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Current Implementation Status](#current-implementation-status)
- [Evaluation and Reproducibility](#evaluation-and-reproducibility)
- [Security and Reliability](#security-and-reliability)
- [Future Improvements](#future-improvements)
- [Demo](#demo)
- [Repository](#repository)
- [License](#license)

---

## Problem Statement

Every returned product needs to be inspected to answer five questions:

1. Is this the expected product? (**identity**)
2. Are the required components and accessories present? (**completeness**)
3. What is its physical **condition**?
4. What should happen to it? (**disposition**)
5. Can the decision be supported with **evidence**?

Inconsistent manual inspection leads to incorrect decisions, missing evidence, and no reliable way to trace why a return was restocked, refurbished, liquidated, disposed of, or sent for review.

## Solution

The system separates observation from decision:

<div align="center">

**AI observes → Rules decide → Humans resolve uncertainty**

</div>

- The **vision layer** only extracts structured observations from images (`OBSERVED`, `NOT_OBSERVED`, or `UNCERTAIN`). It does not choose a disposition.
- A **deterministic rules engine** (`src/engine.py`) makes the final disposition, so the same observations always produce the same outcome and the logic can be tested.
- When identity or completeness is uncertain, or a condition is unknown, the record goes to `pending_review` instead of an automated commercial action.

## Workflow

<div align="center">
<img src="docs/assets/pipeline.svg" alt="Animated inspection pipeline" width="100%"/>
</div>

```mermaid
flowchart TD
    A[Return item] --> B[QR binding lookup<br/>manual entry, standalone]
    A --> C[Photo capture / upload<br/>POST /media]
    C --> D[Image validation<br/>type, content, size limits]
    D --> E[YOLOv8 detector<br/>optional]
    D --> F[Qwen3-VL via Ollama<br/>visual observations]
    E -.-> G
    F --> G[Structured observations<br/>OBSERVED / NOT_OBSERVED / UNCERTAIN]
    G --> H[Identity check]
    G --> I[Completeness check]
    G --> J[Condition mapping]
    H --> K[Deterministic disposition<br/>src/engine.py]
    I --> K
    J --> K
    K --> L[Decision record<br/>checks, evidence refs, content hash]
    L --> M{Needs review?}
    M -- no --> N[Final decision]
    M -- yes --> O[Human review<br/>POST /reviews/id/resolve]
    O --> N

    classDef opt stroke-dasharray: 5 5;
    class E,B opt;
```

| Stage | What happens |
|---|---|
| QR binding lookup | `POST /authentication/verify` checks a manually typed product/package QR pair against a demo binding. It is an auxiliary lookup, not proof of physical authenticity. |
| Capture and upload | The mobile app uploads photos to `POST /media`, which returns a storage reference. |
| Image validation | Uploads are checked for MIME type, image content, and the 10 MiB limit. Invalid, small, or oversized files are rejected. |
| Vision | Qwen3-VL:8B is asked for observations about the images. An optional YOLO detector is also present in `src/`. |
| Checks | The rules engine evaluates identity, completeness, and condition from the observations plus the supplied return data. |
| Disposition | The engine maps the checks to `restock`, `refurbish`, `liquidate`, `dispose`, or `pending_review`. |
| Record | A decision record with checks, evidence references, and a content hash is persisted. |
| Review | Operators list pending records and resolve them through the review endpoints. |

## Core Inspection Checks

| Check | Purpose | Output |
|---|---|---|
| Identity | Compare the observed product against the expected SKU/ASIN. Only a legible identifier seen in an image supports a match. | `PASS` / `FAIL` / `UNCERTAIN` |
| Completeness | Check observed components against the expected `parts_list`. A part not observed in images is not treated as proof of absence. | `PASS` / `FAIL` / `UNCERTAIN` |
| Condition | Map the observed state to the Amazon condition scale used by the project (for example New, Used - Like New, Used - Very Good, Used - Good, Used - Acceptable, Unacceptable). Unknown conditions route to review. | Condition result |
| Disposition | Combine the three checks with deterministic rules. | `restock` / `refurbish` / `liquidate` / `dispose` / `pending_review` |

The exact condition mappings and disposition rules live in [`src/engine.py`](src/engine.py); no extra thresholds are defined outside it.

## AI Architecture

### YOLOv8

An optional YOLO detector exists in `src/`, configured through `YOLO_MODEL_PATH`, `YOLO_CONFIDENCE_THRESHOLD`, and `YOLO_IOU_THRESHOLD`. The `yolov8n.pt` weights file is committed at the repository root. `ultralytics` is **not** listed in `requirements.txt`, so YOLO detection is not part of the default install, and its end-to-end contribution to decisions has not been verified.

### Qwen3-VL:8B

Qwen3-VL:8B runs locally through Ollama and is the vision provider. It is given the expected SKU/ASIN as reference values and returns visual observations about identity, parts, and condition. It does not decide the disposition. If the provider fails or times out, no observations are produced, so the checks become `UNCERTAIN` and the record goes to `pending_review`.

> Live inference is **not verified** on the development machine: the real-image request timed out after 300 seconds.

### Deterministic Decision Engine

The final disposition comes from rules rather than from the LLM because:

- the same observations always give the same outcome, which makes behavior testable without a model;
- a vision-model error can only make a check uncertain, not silently trigger a restock or disposal;
- the reason for each outcome can be traced to named checks rather than free-form model text.

## System Architecture

```mermaid
flowchart LR
    subgraph Client
        M[mobile/ React + Vite]
        W[website/ React + Vite]
    end

    subgraph Backend[FastAPI backend - src/]
        R[Routes]
        V[Image validation]
        S[(Storage adapter<br/>local or S3-compatible)]
        P[Vision providers<br/>Ollama Qwen3-VL / optional YOLO]
        E[Decision engine]
        DB[(SQLAlchemy<br/>SQLite default / PostgreSQL)]
    end

    M --> R
    W --> R
    R --> V --> S
    V --> P --> O[Structured observations]
    O --> E --> DB
    DB --> H[Human review endpoints]
    H --> DB
```

## Technology Stack

| Category | Technology | Purpose |
|---|---|---|
| Language | Python 3.11+ | Backend |
| API framework | FastAPI, Uvicorn | HTTP API and server |
| Validation | Pydantic | Request and decision-record schemas |
| Database | SQLAlchemy, SQLite (default), PostgreSQL via `psycopg2-binary` | Persistence; PostgreSQL is opt-in through `DATABASE_URL` |
| Images | Pillow, `python-multipart` | Upload handling and image validation |
| Vision model | Ollama + Qwen3-VL:8B | Visual observations |
| Detector | YOLOv8 weights (`yolov8n.pt`), optional | Optional object detection; not in `requirements.txt` |
| Storage | Local filesystem; S3-compatible via `boto3` | Image storage |
| HTTP client | `requests` | Calling Ollama |
| Frontend | React, Vite, Node.js/npm | `mobile/` and `website/` apps |
| Testing | pytest, httpx | Unit and API tests |

## Backend

- **FastAPI** serves the API from `src/main:app` on port `8000`.
- **Validation:** Pydantic schemas validate inputs and shape the `DecisionRecord`; invalid payloads return `422`. Media uploads are validated for MIME type, image content, and the 10 MiB limit.
- **Database layer:** SQLAlchemy models and a repository layer in `src/`; SQLite by default.
- **Decision engine:** `src/engine.py` holds condition mappings and disposition rules.
- **Human review:** pending records are listed and resolved through dedicated endpoints; client-supplied `operator_disposition` is not applied as an override.
- **Evidence:** each record keeps checks, evidence references, and a content hash.

**Endpoints**

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Service status |
| `POST` | `/media` | Upload and validate an image; returns a storage reference |
| `GET` | `/media/{media_id}?organization_id=...` | Fetch image bytes after an organization check |
| `POST` | `/authentication/bind` | Create a demo product/package QR binding |
| `POST` | `/authentication/verify` | Verify a QR pair; returns `qr_auth_result` and `auth_event_id` |
| `POST` | `/inspect` (also `/agent`) | Run the vision and decision pipeline for a return |
| `GET` | `/returns/{record_id}` | Fetch a decision record |
| `GET` | `/returns/{record_id}/evidence?org_id=...` | List evidence metadata and media IDs |
| `GET` | `/reviews` | List records awaiting review |
| `POST` | `/reviews/{record_id}/resolve` | Resolve a pending record |

See [`docs/API.md`](docs/API.md) for request and response details.

## Frontend

The repository contains two separate React/Vite apps:

- **`mobile/`** is the app launched by `start_demo.py` (port `5173`). The implemented flow is: dashboard, manual package/product QR entry and verification, photo capture or upload, inspection, then result and review. The photo picker can request a rear-camera capture on supported devices, but no physical phone-camera test was performed.
- **`website/`** is a separate app that is built as part of the verification commands.

QR values are typed manually. There is no camera QR decoder and no hidden or obscured barcode implementation.

## Data and Evidence

| Item | How it is handled |
|---|---|
| Observations and checks | Each check stores `check_key`, `verdict`, `confidence`, `detail`, `model_version`, `evidence_refs`, and a timestamp. |
| Image references | Records list their image paths; uploaded media is stored with a SHA-256 checksum and tied to an organization ID. |
| Evidence listing | `GET /returns/{record_id}/evidence` returns metadata and media IDs without exposing storage paths. |
| Decision record | `DecisionRecord` includes `outcome`, `status`, `overrides`, `correlation_id`, and `content_hash`. |
| Human overrides | Stored in `overrides`; the original verdict is preserved alongside the revised one. |
| Integrity | `content_hash` covers selected decision fields. It is **not** a signature and **not** a hash of all evidence; the media SHA-256 is separate. |

## Human-in-the-Loop

Review is triggered when:

- identity or completeness is `UNCERTAIN`;
- a condition is unknown;
- the vision provider returns nothing (error or timeout), which yields uncertain checks.

`UNCERTAIN` is handled differently from a definitive `PASS` or `FAIL`: it never leads to an automated commercial disposition and always lands in `pending_review`. An operator resolves the record via `POST /reviews/{record_id}/resolve`; this is the only path that applies an override.

```mermaid
stateDiagram-v2
    [*] --> Inspected
    Inspected --> Decided: all checks PASS or FAIL
    Inspected --> pending_review: any UNCERTAIN, unknown condition, or vision error
    pending_review --> Resolved: operator resolves via /reviews
    Decided --> [*]
    Resolved --> [*]
```

## API / Workflow Example

> Illustrative shape taken from `docs/API.md`; it is **not** a captured live response.

**Input:** a return, the expected product information, and image references.

```json
{
  "record_id": "RTN-0003",
  "unit_id": "UNIT-0003",
  "org_id": "org_demo_bravo",
  "ordered_sku": "SKU-PUZZLE-500",
  "ordered_asin": "B0DUMMY729",
  "parts_list": "puzzle pieces;poster",
  "observed_state": "signs_of_use",
  "photo_refs": "fixtures/returns/UNIT-0003_1.jpg;fixtures/returns/UNIT-0003_2.jpg"
}
```

**Processing:** vision → observations → checks → decision engine.

**Output (abbreviated):**

```json
{
  "record_id": "RTN-0003",
  "organization_id": "org_demo_bravo",
  "checks": [
    {
      "check_key": "identity",
      "verdict": "UNCERTAIN",
      "confidence": 0.0,
      "detail": "No legible matching product identifier was observed.",
      "model_version": "qwen3-vl:8b"
    }
  ],
  "outcome": "pending_review",
  "overrides": [],
  "status": "pending_review",
  "content_hash": "..."
}
```

## Installation

Requirements: Python 3.11+, Node.js/npm, and Ollama for real model inference.

```bash
# 1. Clone
git clone https://github.com/Adithya-charan/cube-04-returns-manager.git
cd cube-04-returns-manager

# 2. Create a virtual environment
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate

# 3. Install backend dependencies
python -m pip install -r requirements.txt

# 4-5. Start Ollama and pull the vision model
ollama serve
ollama pull qwen3-vl:8b
```

**Quick start (backend and mobile app together):**

```bash
python start_demo.py
```

This starts FastAPI on port `8000` and the mobile Vite app on port `5173`. For a phone on the LAN, the launcher points the frontend at the host's detected LAN address.

**Or run them separately:**

```bash
# Backend
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000

# Frontend (second terminal)
cd mobile
npm install
npm run dev
```

The API does **not** load `.env` automatically. Set variables in the process environment (see below).

## Environment Variables

Documented in `.env.example`. No external AI API keys are required.

| Variable | Default / example | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_VISION_MODEL` | `qwen3-vl:8b` | Vision model name |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Vision request timeout |
| `DATABASE_URL` | `sqlite:///./returns_manager.db` | Database; set a `postgresql+psycopg2://user:password@host/db` URL to use PostgreSQL |
| `YOLO_MODEL_PATH` | `yolov8n.pt` | YOLO weights path |
| `YOLO_CONFIDENCE_THRESHOLD` | `0.25` | YOLO confidence threshold |
| `YOLO_IOU_THRESHOLD` | `0.45` | YOLO IoU threshold |
| `OBJECT_STORAGE_ENDPOINT` | empty | S3-compatible endpoint (optional) |
| `OBJECT_STORAGE_BUCKET` | empty | Bucket name |
| `OBJECT_STORAGE_ACCESS_KEY` | `<your-access-key>` | Storage access key (keep secret) |
| `OBJECT_STORAGE_SECRET_KEY` | `<your-secret-key>` | Storage secret key (keep secret) |
| `CORS_ALLOWED_ORIGINS` | `*` | Allowed CORS origins; restrict this outside local demos |

## Testing

```bash
python -m pytest -q
cd website && npm run build && cd ..
cd mobile && npm run build && cd ..
python e2e_ollama_test.py
```

- Unit and API tests use mocked vision by default; Ollama calls are mocked.
- A passing test suite or build does **not** verify camera scanning or real model inference.
- `e2e_ollama_test.py` runs against a real Ollama instance; its last real-image run timed out at 300 seconds (see below).
- No pass/fail counts or coverage figures are reported here because none are recorded in the repository.

## Project Structure

```text
cube-04-returns-manager/
├── src/                  # FastAPI routes, models, repository, storage adapter,
│                         # Ollama provider, optional YOLO detector, decision engine
├── tests/                # pytest unit and API tests
├── mobile/               # React/Vite app launched by start_demo.py
├── website/              # React/Vite app
├── fixtures/returns/     # Local image test data and fallback media storage
├── data/                 # Sample data
├── evaluation/           # Evaluation-related files
├── docs/                 # ARCHITECTURE.md, API.md, DEMO.md, assets/pipeline.svg
├── submissions/_TEMPLATE # CUBE submission template
├── VerifyMe-temp/        # Unrelated nested checkout (NFT/ERC-721 auth demo); not imported
├── start_demo.py         # Launches backend and mobile app
├── e2e_ollama_test.py    # End-to-end test against real Ollama
├── requirements.txt
├── .env.example
├── yolov8n.pt            # YOLOv8 nano weights
└── returns_manager.db    # Local SQLite database file
```

## Current Implementation Status

### Implemented

- FastAPI API, dashboard, upload path, and review endpoints
- Deterministic rules engine for identity, completeness, condition, and disposition
- `UNCERTAIN` handling that routes to `pending_review`
- Image upload validation (MIME type, image content, 10 MiB limit) and media checksums
- Persisted decision records with checks, evidence references, overrides, and a content hash
- Review resolution route; client-provided `operator_disposition` is not trusted
- Server-issued QR verification event, consumed once by an inspection (demo binding lookup)
- Local storage and an S3-compatible storage adapter
- pytest unit and API tests with mocked vision

- **Live Qwen3-VL inference:** the model is installed locally, but the real-image test timed out after 300 seconds.
- **Physical camera capture:** the mobile picker can request the rear camera, but no physical phone test was performed.
- **QR scanning:** values are typed manually; there is no camera QR decoder or hidden-barcode support. QR verification is not connected to the decision engine and does not bind an order, SKU, or tenant.
- **Image quality:** blur, glare, exposure, and framing are not measured.
- **S3 storage:** implemented, but remote object references are not adapted for the Ollama provider, which reads local file paths, so it is not end-to-end integrated.
- **YOLO:** present as an optional component; not in `requirements.txt` and not verified end to end.
- **Authentication:** the API has no user authentication or authorization; `org_id` is caller-supplied and does not establish identity.
- **Integrity:** `content_hash` is not a signature or an immutable ledger.

## Evaluation and Reproducibility

To reproduce: install the dependencies, run `python -m pytest -q` (mocked vision), and optionally run `python e2e_ollama_test.py` with Ollama and `qwen3-vl:8b` available.

No accuracy, false-positive/false-negative, Cohen's kappa, or 50+ unseen-unit evaluation results are reported in this README, and none should be fabricated. The architecture document describes such an evaluation pipeline as intended work, not as completed results.

## Security and Reliability

Implemented mechanisms:

- Upload validation: MIME type, image content, size limits
- Organization-scoped media and evidence access checks (not authentication)
- One-time consumption of server-issued QR verification events
- Client-supplied `qr_auth_result` and `operator_disposition` are ignored
- Fail-open uncertainty handling: provider errors yield `UNCERTAIN` and `pending_review`
- Content hash on decision records and SHA-256 checksums on uploaded media
- Original AI verdicts preserved when a human override is recorded

**Not production-ready:** no user authentication, caller-supplied tenant IDs, and `CORS_ALLOWED_ORIGINS=*` by default. Do not expose this demo API publicly.

## Future Improvements

Planned or suggested work, none of which is part of the current implementation:

- Larger held-out evaluation set with independent human labels and reported metrics
- Image quality assessment (blur, glare, exposure, framing)
- Production authentication and tenant binding
- End-to-end remote storage support for the vision provider
- Camera-based QR scanning
- Faster or more reliable local vision inference
- Stronger integrity (signed or append-only decision records)

## Demo

Demo URL: <https://cube-04-returns-manager-mu.vercel.app> (listed in the repository's About field; what it serves, and whether it is connected to a working backend, has not been verified).

Additional walkthrough notes: [`DEMO_FLOW.md`](DEMO_FLOW.md) and [`docs/DEMO.md`](docs/DEMO.md).

## Repository

https://github.com/Adithya-charan/cube-04-returns-manager

This repository is a fork of `Cube-Build-A-Thon/cube-04-returns-manager`.

See also: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/API.md`](docs/API.md).

## License

No license file is present in the repository root, so no license is currently specified.

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0c4a6e,50:1e1b4b,100:0f172a&height=100&section=footer" alt="" width="100%"/>

</div>
