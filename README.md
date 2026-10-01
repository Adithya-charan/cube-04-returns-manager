# CUBE Returns Manager

A local-first returns inspection prototype. FastAPI accepts product references and uploaded images, Ollama/Qwen3-VL is asked for visual observations, and a deterministic Python engine maps those observations to identity, completeness, condition, and disposition checks. Ambiguous results can be resolved through a human-review endpoint.

## Current Status

This is a demo, not a production-secure multi-tenant service. The API, dashboard, upload path, deterministic rules, and review endpoints exist. The mobile photo picker can request a rear-camera capture on supported devices, but no physical phone-camera test was performed. QR values are entered manually; there is no camera QR decoder or hidden/obscured barcode implementation. QR verification is an auxiliary binding lookup, not proof of physical authenticity.

Qwen3-VL:8B is installed locally, but the real-image test timed out after 300 seconds. The model path is therefore **not verified** on this machine. Image checks reject invalid, small, or oversized files; blur, glare, exposure, and framing are not currently measured. S3-compatible upload is implemented, but remote object references are not currently adapted for the Ollama provider, which reads local file paths.

## Project Layout

- `mobile/` and `website/`: separate React/Vite apps. `start_demo.py` launches `mobile/`.
- `src/`: FastAPI routes, SQLAlchemy models/repository, local/S3 storage adapter, Ollama provider, optional YOLO detector, and decision engine.
- `tests/`: pytest unit and API tests. Ollama calls are mocked by default.
- `fixtures/returns/`: local image test data and fallback media storage.
- `VerifyMe-temp/`: nested Git checkout of an unrelated NFT/ERC-721 product-authentication demo. It generates QR codes but contains no scanner or hidden-barcode decoder and is not imported by the Returns Manager.

## Setup

Requirements: Python 3.11+, Node.js/npm, and Ollama for real model inference. SQLite is the local default. Environment variables are read from the process environment; the API does not automatically load `.env`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
ollama serve
ollama pull qwen3-vl:8b
python start_demo.py
```

The demo starts FastAPI on port `8000` and the mobile Vite app on port `5173`. For a phone on the LAN, the launcher configures the frontend API URL to the host's detected LAN address. Browser `getUserMedia` scanning would require HTTPS or localhost; it is not implemented here.

To run the backend and frontend separately:

```powershell
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
Set-Location mobile
npm install
npm run dev
```

Set `DATABASE_URL` in the process environment to opt into PostgreSQL. The included `.env.example` documents Ollama, database, YOLO, storage, and CORS settings but is not loaded automatically. S3-compatible storage uses `OBJECT_STORAGE_ENDPOINT`, `OBJECT_STORAGE_BUCKET`, `OBJECT_STORAGE_ACCESS_KEY`, and `OBJECT_STORAGE_SECRET_KEY`.

## Workflow And API

The current UI path is dashboard → manual package/product QR entry and `/authentication/verify` → photo capture/upload to `/media` → `/inspect` → observations and rule checks → result/review. Authentication is a standalone binding lookup: its result is not connected to the inspection record, and client-supplied QR results are ignored by the decision engine. Identity requires visual evidence containing the expected SKU.

Key routes: `GET /health`, `POST /media`, `GET /media/{media_id}`, `POST /authentication/bind`, `POST /authentication/verify`, `POST /inspect` (also `/agent`), `GET /returns/{record_id}`, `GET /reviews`, and `POST /reviews/{record_id}/resolve`.

Current condition mappings and disposition rules are in `src/engine.py`. Unknown conditions and uncertain identity/completeness route to `pending_review`. Client-provided `operator_disposition` does not apply an override; use the review-resolution route. The content hash covers only record ID, outcome, override count, and status; it is not a signature or a complete hash of all evidence.

## Verification

```powershell
python -m pytest -q
Push-Location website; npm run build; Pop-Location
Push-Location mobile; npm run build; Pop-Location
python e2e_ollama_test.py
```

Tests use mock vision by default. A passing test suite/build does not verify camera scanning or real model inference. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/API.md](docs/API.md), and [docs/DEMO.md](docs/DEMO.md) for implementation boundaries and route details.
