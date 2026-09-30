# CUBE Returns Manager

An autonomous, multi-tenant enabled backend orchestration engine designed for securely mapping return processing data between Vision AI Providers and Deterministic Final Rules. Built during the CUBE Build-A-Thon 2026.

## Features Complete
- **Multi-tenant Data Boundaries**: Segregates API execution logic strictly preventing Cross-Tenant leakage natively through DB bounds.
- **Fail-Open System**: AI Uncertainty falls back securely to `pending_review`. Human operators can execute trace-locked overrides.
- **Cross-Pod Verification**: Output conforms purely to authoritative Data bounds matching standard UUID hashing logic ensuring data structure immutability across services.
- **Extensible Vision Engine**: Plug-and-play abstraction model with `OllamaQwenVisionProvider` (production, local Ollama + qwen3-vl:8b) and `MockVisionProvider` (tests only).
- **Mobile Responsive Frontend**: Fully working Vite/React/Tailwind dashboard enabling operator review, ingestion logging, and override logic directly against live backend.
- **Local AI Inference**: Runs entirely on local Ollama with qwen3-vl:8b — no external API keys required.
- **Deterministic Disposition Rules**: Identity → Completeness → Condition → Disposition with full evidence trail.
- **Human-in-the-Loop**: Uncertain cases route to `pending_review` with operator override preserving original AI verdict.

## Tech Stack
- **Backend API**: Python 3.12, FastAPI, Pydantic, SQLAlchemy.
- **Testing**: Pytest scaling Unit and Component mappings.
- **Frontend**: React, Vite, Tailwind CSS, Lucide Icons.
- **Vision AI**: Local Ollama + qwen3-vl:8b (CPU inference).
- **Database**: SQLite (dev) / PostgreSQL (prod) via SQLAlchemy.

## Quick Start
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Start Ollama (separate terminal)
ollama serve
ollama pull qwen3-vl:8b

# Start demo orchestration
python start_demo.py
```

## Available Scripts & Endpoints
- **GET /health**: Validates application running bounds.
- **POST /inspect**: Orchestrates entire returns pipeline natively.
- **POST /agent**: Alternative endpoint for inspection.
- **GET /returns/{record_id}**: Polls specific generated data cross-pod hash.
- **POST /media**: Upload product images (validated, size-limited, tenant-isolated).
- **GET /media/{media_id}**: Retrieve uploaded media with tenant authorization.
- **GET /reviews & POST /reviews/{id}/resolve**: Human-in-the-loop fallback execution engine.

## AI Architecture
```
Phone Camera → React Frontend (LAN) → FastAPI (0.0.0.0:8000)
    → Image Upload → Ollama (localhost:11434)
    → qwen3-vl:8b → Structured Observations
    → Deterministic Rules Engine
    → Disposition + Evidence
    → Frontend Display
```

**Key Principle**: Phone NEVER communicates directly with Ollama. All AI inference is server-side via FastAPI.

*Please see docs/DEMO.md for explicit application testing sequences mapped via visual frontend parameters.*
