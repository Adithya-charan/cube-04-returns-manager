# CUBE Returns Manager — Demo Preparation Flow (3-5 minutes)

## Pre-Demo Checklist (Run 10 minutes before)

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Verify model
ollama pull qwen3-vl:8b

# Terminal 3: Start automated demo
# from within the project root folder
python start_demo.py
```

**Wait for**: LAN IP display, health checks, "SYSTEM ONLINE"

## Demo Flow (3-5 minutes)

### 1. Problem Statement (30s)
> "Returns processing requires answering 4 questions: Is this the item sold? Is it complete? What condition? What next? We do this with local AI + deterministic rules."

### 2. Show Return Product (30s)
> Hold up a physical product (e.g., Bluetooth speaker with cable + manual)
> "This is what we're inspecting. SKU: SKU-SPEAKER-500. Expected: cable;manual"

### 3. Open Mobile Interface (20s)
> On phone: Open `http://<LAN-IP>:5173`
> Show: "New Inspection" button, pending reviews list

### 4. Capture Image (30s)
> Tap "Start Inspection"
> Enter SKU: `SKU-SPEAKER-500`
> Enter Parts: `cable;manual`
> Tap **Camera** → Allow permission → Capture photo
> Show preview grid
> Tap **Process Return**

### 5. AI Processing (15-60s depending on warm/cold)
> Show progressive status:
> - "Sending to Ollama qwen3-vl:8b…"
> - "Analyzing product identity…"
> - "Checking included components…"
> - "Evaluating visible condition…"
> - "Preparing return decision…"
> **Explain**: "Local Ollama on CPU, first run ~4 min, subsequent ~1 min"

### 6. Show Identity Evidence (20s)
> Result screen shows:
> - **Disposition Badge**: RESTOCK (green)
> - **Identity Check**: PASS — "brand label 'soundcore' visible on speaker"
> - **Confidence**: 90%
> "AI observed the brand label matches expected SKU"

### 7. Show Completeness Evidence (20s)
> - **Completeness Check**: PASS — "USB cable coiled in box" + "user manual present"
> - **Confidence**: 85%
> "Both expected components visually confirmed"

### 8. Show Condition Evidence (20s)
> - **Condition Check**: PASS — "surface appears clean with no visible wear"
> - **No scratches**: NOT_OBSERVED (confidence 90%)
> - **Mapped to**: USED_VERY_GOOD (Amazon scale)
> "Amazon condition scale applied deterministically"

### 9. Show Deterministic Disposition (15s)
> - **Final**: RESTOCK
> - **Rule**: Identity PASS + Completeness PASS + Condition NEW/LIKE_NEW → RESTOCK
> "Rules engine, not AI, made this decision"

### 10. Show Evidence Record (20s)
> Expand checks → show:
> - Correlation ID
> - Model version: qwen3-vl:8b v1.0
> - Latency: ~290s cold
> - Content hash (tamper-evident)

### 11. Demonstrate Human Review (30s)
> **Option A**: Show pending_review from test
> - Dashboard → "Pending Review" → Click eye
> - Show original AI verdict + evidence
> - Select override (e.g., LIQUIDATE)
> - Show: "Original: pending_review → New: liquidate"

### 12. Show Evaluation Metrics (20s)
> "No fabricated metrics. Measured on 50 unseen units with 2 human labels each."
> Show: evaluation/evaluate.py structure

### 13. Architecture Summary (30s)
```
Phone → React → FastAPI → Ollama → qwen3-vl:8b → Rules → Evidence → Decision
```
> "No external AI. Local Ollama. Deterministic rules. Human review when uncertain."

### 14. Uncertainty Handling (20s)
> "NOT_OBSERVED ≠ MISSING. Uncertain = human review. No fabricated confidence."

### 15. Q&A / Close (30s)

---

## Demo Scripts

### Scenario 1: Complete Pass (RESTOCK)
- Product: Complete, good condition
- Expected: Identity PASS, Completeness PASS, Condition NEW/LIKE_NEW → RESTOCK

### Scenario 2: Missing Component (LIQUIDATE)
- Product: Cable removed from box
- Expected: Identity PASS, Completeness FAIL → LIQUIDATE

### Scenario 3: Wrong Product (DISPOSE)
- Product: Different item in box
- Expected: Identity FAIL → DISPOSE

### Scenario 4: Ambiguous (PENDING_REVIEW)
- Product: Blurry photo, occluded components
- Expected: Identity/Completeness UNCERTAIN → PENDING_REVIEW

### Scenario 5: Damaged (DISPOSE or LIQUIDATE)
- Product: Visible scratches/dents
- Expected: Condition UNACCEPTABLE → DISPOSE (if complete) or DISPOSE (if incomplete)

---

## Demo Talking Points

| Topic | Key Message |
|-------|-------------|
| **Local AI** | "Ollama + qwen3-vl:8b runs on this laptop. No API keys. No cloud." |
| **Deterministic Rules** | "AI observes. Rules decide. No hallucinated dispositions." |
| **Uncertainty** | "UNCERTAIN is a first-class verdict. Routes to human, not guess." |
| **Evidence** | "Every observation has visual evidence. Content hash = tamper-evident." |
| **Human Override** | "Original AI verdict preserved. Operator accountable." |
| **No Fabrication** | "No 98% accuracy claims. Physical evaluation required for real metrics." |

---

## Emergency Fallback

If Ollama fails during demo:
1. Explain: "Fail-open design — system routes to pending_review"
2. Show: `/reviews` endpoint with "Ollama unavailable" error
3. Demonstrate: Human override still works with manual inspection