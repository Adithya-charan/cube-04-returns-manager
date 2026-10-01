"""
OllamaQwenVisionProvider — production vision provider.

Uses the local Ollama HTTP API (http://localhost:11434) with model qwen3-vl:8b.
No external API keys required.

Architecture:
    Browser → FastAPI → Ollama (local) → qwen3-vl:8b → structured observations
"""

import os
import time
import json
import base64
import re
import requests
import logging
import threading
from typing import List, Optional
from io import BytesIO
from PIL import Image
from .vision import VisionProvider, VisionResult, VisionObservation
from .models import EvidenceState

# Configure module logger
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "qwen3-vl:8b")

# Timeout for vision inference (qwen3-vl can be slow on first load, especially on CPU)
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300"))

# Image processing limits for CPU optimization
MAX_IMAGE_DIMENSION = int(os.getenv("MAX_IMAGE_DIMENSION", "1024"))
MAX_IMAGE_SIZE_BYTES = int(os.getenv("MAX_IMAGE_SIZE_BYTES", "4194304"))  # 4MB
MIN_IMAGE_DIMENSION = int(os.getenv("MIN_IMAGE_DIMENSION", "64"))

INSPECTION_PROMPT_TEMPLATE = """You are a product returns inspector. Examine the image and report ONLY what is visually observable.

STRICT RULES:
1. Do NOT make business decisions (restock/refurbish/liquidate/dispose/pending_review).
2. Do NOT fabricate observations. If unclear, mark as UNCERTAIN.
3. Do NOT infer missing components from empty space unless the compartment is clearly visible and empty.
4. Do NOT assume a component is missing because it is not visible — use UNCERTAIN.
5. Do NOT invent accessories not in the expected parts list.
6. Do NOT report model numbers, SKUs, or serial numbers unless text is clearly legible in the image.
    6a. Expected identifiers are reference data only. Never repeat one as an observation unless the exact identifier is visibly legible in a submitted image.
7. Do NOT report damage unless visible evidence exists (scratches, dents, cracks, stains, broken parts).
8. IMPORTANT: NOT_OBSERVED does NOT mean MISSING. Use UNCERTAIN if you cannot tell.

Expected components to check: {expected_parts}
Expected product identifiers for visual verification only: {identity_guidance}
Operator condition note: {condition_hint}
Images supplied: {image_count}. They are numbered from 0 in the order provided. Include an integer image_index on every observation identifying its supporting image. If no single image supports it, omit image_index.

VISUAL EVIDENCE REQUIREMENTS:
- Every observation MUST include specific visual evidence from the image
- Confidence must reflect actual visual clarity (0.5 = barely visible, 0.9 = unambiguous)
- For text/OCR: quote the exact text seen, note if partially legible
- For components: describe location, orientation, and visibility
- For condition: describe specific wear/damage markers observed
- For condition_observations, use a name from the configured Amazon mapping only when evidence supports it: factory_sealed, opened_unused, signs_of_use, used_good, used_acceptable, damaged. Otherwise use UNCERTAIN.

Respond ONLY with valid JSON in this exact structure:
{{
  "product_identity_observations": [
    {{"type": "identity", "name": "product_label", "status": "PRESENT|UNCERTAIN", "confidence": 0.9, "evidence": "brand label 'soundcore' visible on speaker grille", "image_index": 0}}
  ],
  "visible_components": [
    {{"type": "completeness", "name": "cable", "status": "PRESENT|MISSING|UNCERTAIN|NOT_VERIFIED", "confidence": 0.85, "evidence": "USB-C cable coiled in upper compartment of box", "image_index": 1}}
  ],
  "condition_observations": [
        {{"type": "condition", "name": "signs_of_use", "status": "PRESENT|UNCERTAIN", "confidence": 0.8, "evidence": "light surface wear visible on the lower edge", "image_index": 2}}
  ],
  "damage_observations": [
    {{"type": "damage", "name": "scratch", "status": "PRESENT|NOT_OBSERVED|UNCERTAIN", "confidence": 0.9, "evidence": "scratch visible on matte black surface", "image_index": 3}}
  ],
  "text_observations": [
    {{"type": "text", "name": "ocr_label", "status": "PRESENT|UNCERTAIN", "confidence": 0.85, "evidence": "text 'soundcore' and 'User Manual' legible on manual cover", "image_index": 1}}
  ],
  "uncertainties": [
    "Cable compartment partially occluded by packaging flap"
  ],
  "evidence": [],
  "image_quality": "GOOD|FAIR|POOR"
}}
"""


def _validate_and_process_image(image_path: str) -> Optional[str]:
    """
    Validate image quality and resize if needed for CPU optimization.
    Returns base64 encoded image or None if validation fails.
    """
    try:
        with open(image_path, "rb") as f:
            content = f.read()
    except (FileNotFoundError, OSError) as e:
        logger.warning(f"Failed to read image {image_path}: {e}")
        return None

    if len(content) == 0:
        logger.warning(f"Image {image_path} is empty")
        return None

    if len(content) > MAX_IMAGE_SIZE_BYTES:
        logger.warning(f"Image {image_path} exceeds max size ({len(content)} > {MAX_IMAGE_SIZE_BYTES})")
        return None

    try:
        img = Image.open(BytesIO(content))
        img.verify()  # Verify it's a valid image
        img = Image.open(BytesIO(content))  # Reopen after verify
    except Exception as e:
        logger.warning(f"Image {image_path} is invalid: {e}")
        return None

    width, height = img.size

    if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
        logger.warning(f"Image {image_path} too small ({width}x{height})")
        return None

    # Resize if image is too large (helps with CPU inference speed)
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
        logger.info(f"Resized image {image_path} from {width}x{height} to {img.size[0]}x{img.size[1]}")
        buffer = BytesIO()
        img.save(buffer, format=img.format or "JPEG")
        content = buffer.getvalue()

    return base64.b64encode(content).decode("utf-8")


def _parse_ollama_response(raw: str, images: List[str]) -> List[VisionObservation]:
    """
    Parse the structured JSON response from Qwen3-VL into VisionObservation objects.
    Strict validation - rejects malformed responses to avoid fabricated observations.
    """
    # Strip markdown fences if model wraps output
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    # Remove <think>...</think> blocks (qwen3 thinking output)
    cleaned = re.sub(r"<think>", "", cleaned, flags=re.DOTALL).strip()
    # Remove 你问...回答 blocks (Chinese thinking output variant)
    cleaned = re.sub(r"你问.*?回答", "", cleaned, flags=re.DOTALL).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try extracting first JSON object from response
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from model response")
                return []
        else:
            logger.warning("No JSON object found in model response")
            return []

    # Validate required top-level keys exist
    required_sections = [
        "product_identity_observations",
        "visible_components",
        "condition_observations",
        "damage_observations",
        "text_observations",
    ]
    for section in required_sections:
        if section not in data:
            logger.warning(f"Missing required section in response: {section}")
            return []

    # Map Qwen status strings → EvidenceState
    STATUS_MAP = {
        "PRESENT": EvidenceState.OBSERVED,
        "MISSING": EvidenceState.MISSING,
        "UNCERTAIN": EvidenceState.UNCERTAIN,
        "NOT_VERIFIED": EvidenceState.UNCERTAIN,
        "NOT_OBSERVED": EvidenceState.NOT_OBSERVED,
    }

    ALLOWED_STATES = set(STATUS_MAP.keys())
    ALLOWED_TYPES = {"identity", "completeness", "condition", "damage", "text"}

    observations = []

    def _extract(section_key: str, default_type: str):
        for item in data.get(section_key, []):
            # Validate required fields
            if not isinstance(item, dict):
                continue
            
            name = item.get("name")
            if not name or name == "unknown":
                continue
            
            raw_status = str(item.get("status", "UNCERTAIN")).upper()
            if raw_status not in ALLOWED_STATES:
                logger.warning(f"Invalid status '{raw_status}' for {name}, defaulting to UNCERTAIN")
                raw_status = "UNCERTAIN"
            state = STATUS_MAP[raw_status]
            
            obs_type = item.get("type", default_type)
            if obs_type not in ALLOWED_TYPES:
                obs_type = default_type
            
            try:
                confidence = float(item.get("confidence", 0.5))
                confidence = max(0.0, min(1.0, confidence))  # Clamp to [0,1]
            except (ValueError, TypeError):
                confidence = 0.5
            
            evidence = item.get("evidence", "No description")
            if not evidence or evidence == "No description":
                logger.warning(f"Missing evidence for observation: {name}")

            image_index = item.get("image_index")
            if image_index is None and len(images) == 1:
                image_index = 0
            image_ref = images[image_index] if isinstance(image_index, int) and not isinstance(image_index, bool) and 0 <= image_index < len(images) else ""
            
            observations.append(VisionObservation(
                observation_type=obs_type,
                object_name=name,
                state=state,
                confidence=confidence,
                evidence_desc=f"[{default_type}] {evidence}",
                image_reference=image_ref
            ))

    _extract("product_identity_observations", "identity")
    _extract("visible_components", "completeness")
    _extract("condition_observations", "condition")
    _extract("damage_observations", "damage")
    _extract("text_observations", "text")

    if not observations:
        logger.warning("No valid observations extracted from model response")

    return observations


class OllamaQwenVisionProvider(VisionProvider):
    """
    Production vision provider using local Ollama + qwen3-vl:8b.

    No API keys. No external services.
    Configured via environment variables:
        OLLAMA_BASE_URL         (default: http://localhost:11434)
        OLLAMA_VISION_MODEL     (default: qwen3-vl:8b)
        OLLAMA_TIMEOUT_SECONDS  (default: 300)
        MAX_IMAGE_DIMENSION     (default: 1024) - resize limit for CPU optimization
        MAX_IMAGE_SIZE_BYTES    (default: 4194304) - 4MB max upload size
        MIN_IMAGE_DIMENSION     (default: 64) - minimum image dimension

    Multi-image attribution:
        Observations receive an image reference only when the model returns a
        valid zero-based image_index. Missing or invalid indices remain
        unattributed instead of being assigned to the first image.

    Concurrent Request Safety:
        Uses a thread lock to serialize requests to Ollama, preventing CPU
        contention when multiple inspections are submitted simultaneously.
        This ensures each inference gets full CPU resources.
    """

    # Class-level lock to serialize requests across all provider instances
    _request_lock = threading.Lock()

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip("/")
        self.model = model or OLLAMA_VISION_MODEL
        self.timeout = timeout or OLLAMA_TIMEOUT_SECONDS
        self.provider = "ollama"

    def _check_ollama_alive(self) -> bool:
        """Ping Ollama to verify it is running."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def _check_model_available(self) -> bool:
        """Verify the target model is installed in Ollama."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code != 200:
                return False
            models = resp.json().get("models", [])
            return any(m.get("name", "").startswith(self.model.split(":")[0]) for m in models)
        except Exception:
            return False

    def inspect(
        self,
        images: List[str],
        expected_parts: List[str],
        condition_guidance: Optional[str] = None,
        identity_guidance: Optional[str] = None,
    ) -> VisionResult:
        """
        Inspect images with request serialization to prevent CPU contention.
        
        Uses a class-level lock to ensure only one inference runs at a time,
        preventing CPU contention when multiple requests arrive simultaneously.
        """
        with self._request_lock:
            return self._inspect_impl(images, expected_parts, condition_guidance, identity_guidance)

    def _inspect_impl(
        self,
        images: List[str],
        expected_parts: List[str],
        condition_guidance: Optional[str] = None,
        identity_guidance: Optional[str] = None,
    ) -> VisionResult:
        start_time = time.time()

        # ── Pre-flight checks ─────────────────────────────────────────────
        if not self._check_ollama_alive():
            return VisionResult(
                observations=[],
                model_name=self.model,
                model_version="unknown",
                provider=self.provider,
                latency_ms=int((time.time() - start_time) * 1000),
                error="Ollama is not running. Start with: ollama serve"
            )

        if not self._check_model_available():
            return VisionResult(
                observations=[],
                model_name=self.model,
                model_version="unknown",
                provider=self.provider,
                latency_ms=int((time.time() - start_time) * 1000),
                error=f"Model '{self.model}' not installed. Run: ollama pull {self.model}"
            )

        # Build combined prompt with JSON schema embedded (works better with qwen3-vl)
        prompt_text = INSPECTION_PROMPT_TEMPLATE.format(
            expected_parts=", ".join(expected_parts) if expected_parts else "unspecified",
            identity_guidance=identity_guidance or "none provided",
            condition_hint=condition_guidance or "none provided",
            image_count=len(images),
        )

        # Encode images that exist on disk
        encoded_images = []
        valid_image_refs = []
        invalid_images = []
        for img_path in images:
            b64 = _validate_and_process_image(img_path)
            if b64:
                encoded_images.append(b64)
                valid_image_refs.append(img_path)
            else:
                invalid_images.append(img_path)

        if invalid_images:
            return VisionResult(
                observations=[],
                model_name=self.model,
                model_version="unknown",
                provider=self.provider,
                latency_ms=int((time.time() - start_time) * 1000),
                error=f"No valid images for inspection; image validation failed for: {invalid_images}",
            )

        if not encoded_images:
            return VisionResult(
                observations=[],
                model_name=self.model,
                model_version="unknown",
                provider=self.provider,
                latency_ms=int((time.time() - start_time) * 1000),
                error=f"No valid images found on disk. Checked: {images}"
            )

        # Use /api/generate with format=json — forces valid JSON output
        payload = {
            "model": self.model,
            "prompt": prompt_text,
            "images": encoded_images,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "num_predict": 4096,
            },
        }

        # ── Call Ollama API ───────────────────────────────────────────────
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.Timeout:
            return VisionResult(
                observations=[],
                model_name=self.model,
                model_version="unknown",
                provider=self.provider,
                latency_ms=int((time.time() - start_time) * 1000),
                error=f"Ollama request timed out after {self.timeout}s"
            )
        except requests.RequestException as exc:
            return VisionResult(
                observations=[],
                model_name=self.model,
                model_version="unknown",
                provider=self.provider,
                latency_ms=int((time.time() - start_time) * 1000),
                error=f"Ollama HTTP error: {exc}"
            )

        # ── Parse response ────────────────────────────────────────────────
        try:
            resp_json = resp.json()
            # /api/generate returns: {"response": "...", "done": true, ...}
            raw_content = resp_json.get("response", "")
        except (KeyError, ValueError) as exc:
            return VisionResult(
                observations=[],
                model_name=self.model,
                model_version="unknown",
                provider=self.provider,
                latency_ms=int((time.time() - start_time) * 1000),
                error=f"Malformed Ollama response: {exc}"
            )

        observations = _parse_ollama_response(raw_content, valid_image_refs)

        if not observations:
            # Model responded but we could not parse structured output
            return VisionResult(
                observations=[],
                model_name=self.model,
                model_version="1.0",
                provider=self.provider,
                latency_ms=int((time.time() - start_time) * 1000),
                error=f"Could not parse structured observations from model output. Raw: {raw_content[:300]}"
            )

        return VisionResult(
            observations=observations,
            model_name=self.model,
            model_version="1.0",
            provider=self.provider,
            latency_ms=int((time.time() - start_time) * 1000),
        )
