# Returns Manager: Demo Guide

## Requirements
- Python 3.12+
- Node.js v18+ 
- Local Ollama server running (`ollama serve`) with model `qwen3-vl:8b` pulled (`ollama pull qwen3-vl:8b`).

## Execution

### Local Development (PC only)
```bash
python start_demo.py
```
This launches the backend on port 8000 and the React Frontend on port 5173.

### LAN Development (Phone Demo)
1. Start the demo:
   ```bash
   python start_demo.py
   ```
2. Note the LAN IP shown in the startup output (e.g., `http://192.168.1.50:5173`)
3. On your phone (same Wi-Fi), open the Frontend URL
4. Configure the frontend API base URL if needed:
   - Create `frontend/.env.local` with `VITE_API_BASE=http://<PC-LAN-IP>:8000`
   - Or the app will auto-detect if accessed via LAN IP

## Known Limitations

### Multi-Image Support
The vision provider accepts multiple images but currently only the **first image** is used as the reference for all observations. All images are sent to the model in a single request, but observations are not attributed to specific images. For the demo, use a single clear photo showing the product and all components.

### CPU Inference Latency
- Cold start (first request): ~238 seconds
- Warm (model loaded in memory): ~57 seconds
- The UI displays progressive status messages during inference

## Scenario Procedures

### Scenario A: Complete Return (Pass)
1. Open the frontend UI (http://localhost:5173 or LAN IP).
2. Click **Start New Inspection**.
3. Enter SKU (e.g., `SKU-SPEAKER-500`) and Expected Parts (e.g., `cable;manual`).
4. Capture or upload a clear product photo.
5. Click **Process Return**.
6. Wait for inspection (progressive status: "Analyzing product identity..." → "Checking included components..." → "Evaluating visible condition..." → "Preparing return decision...").
7. Result shows `completed` with disposition `restock` for new/like-new items.

### Scenario B: Missing Component 
1. In a live system, physically remove a component (e.g., cable).
2. Capture photo showing missing component.
3. Submit for inspection.
4. Result: `completeness` check = FAIL → disposition `liquidate` (or `dispose` if damaged).

### Scenario C: Ambiguous Evidence (Uncertainty)
1. Capture a poor quality or ambiguous photo (blurry, dark, occluded).
2. The vision model returns `UNCERTAIN` observations.
3. Rules engine routes to `pending_review`.
5. Dashboard shows "Pending Review" - click to resolve.

### Scenario D: Human Override
1. Locate any `pending_review` block on dashboard list.
2. Click the eye icon (Resolve).
3. Review AI evidence and missing details.
4. Select correct disposition: `restock`, `refurbish`, `liquidate`, or `dispose`.
5. Dashboard updates; original AI verdict preserved in override record.

### Scenario E: Identity Mismatch
1. Enter incorrect SKU that doesn't match the product in the photo.
2. Vision detects different product labels.
3. Identity check = FAIL → disposition `dispose`.

## Architecture Flow

```
Phone Camera → Frontend (LAN) → FastAPI (0.0.0.0:8000) 
    → Image Upload → Ollama (localhost:11434) 
    → qwen3-vl:8b → Structured Observations 
    → Deterministic Rules Engine 
    → Disposition + Evidence 
    → Frontend Display
```

**Note**: Phone NEVER communicates directly with Ollama. All AI inference is server-side.

## Configuration

Environment variables (`.env`):
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_VISION_MODEL=qwen3-vl:8b
OLLAMA_TIMEOUT_SECONDS=300
MAX_IMAGE_DIMENSION=1024
MAX_IMAGE_SIZE_BYTES=4194304
MIN_IMAGE_DIMENSION=64
DATABASE_URL=sqlite:///./returns_manager.db
```

Frontend (`.env.local`):
```
VITE_API_BASE=http://<PC-LAN-IP>:8000
```

## Deployment Decision

For the CUBE hackathon demo, **Option A (Local PC + Phone on same Wi-Fi)** is recommended:

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A: Local PC + Phone** | Laptop runs Ollama + FastAPI + Frontend; phone on same Wi-Fi | No cloud costs, fully offline, low latency LAN | Requires physical laptop at demo |
| B: Cloud VM + Ollama | Dedicated cloud GPU instance running Ollama | Scalable, persistent | Cloud costs, network latency, GPU provisioning |
| C: Hosted AI Provider | External API (OpenAI/Groq/HF) | No local GPU needed | API keys, costs, privacy, NOT allowed for this project |

**Decision**: Use **Option A** for the hackathon demo. Ollama runs locally on the demo laptop, no external API keys required.

## Demo Startup Process

### Automated (Recommended)
```bash
python start_demo.py
```
This script:
1. Detects LAN IP automatically
2. Starts Ollama (must be pre-installed with `qwen3-vl:8b`)
3. Starts FastAPI backend on `0.0.0.0:8000`
4. Starts Vite frontend on `0.0.0.0:5173`
5. Displays LAN URLs for phone access

### Manual Step-by-Step
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Verify model
ollama pull qwen3-vl:8b

# Terminal 3: Start Backend
cd CUBE-Returns-Manager # switch to project root
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Terminal 4: Start Frontend
cd frontend # run from inside the frontend folder
npm run dev
```

### Startup Verification Checklist
After running `start_demo.py`, verify:
- [ ] Ollama: `http://localhost:11434` returns model list
- [ ] Backend: `http://<LAN-IP>:8000/health` returns `{"status":"ok"}`
- [ ] Frontend: `http://<LAN-IP>:5173` loads in browser
- [ ] Phone can access Frontend URL on same Wi-Fi
- [ ] Frontend can POST to Backend `/inspect` endpoint
