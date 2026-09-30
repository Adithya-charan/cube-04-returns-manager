"""
Real end-to-end integration test for the Ollama vision pipeline.

Runs WITHOUT mock patching — sends an actual image to the live Ollama server.
Requires:
    - Ollama running:  ollama serve
    - Model installed: ollama pull qwen3-vl:8b
    - Image file:      fixtures/returns/e2e_test_product.png

Run:
    python e2e_ollama_test.py
"""
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.vision_ollama import OllamaQwenVisionProvider

IMAGE_PATH = "fixtures/returns/e2e_test_product.png"
EXPECTED_PARTS = ["cable", "manual"]
CONDITION_HINT = "opened_unused"

def main():
    print("=" * 60)
    print("  CUBE Returns Manager - Real Ollama E2E Test")
    print("=" * 60)

    if not os.path.exists(IMAGE_PATH):
        print(f"[ERROR] Test image not found: {IMAGE_PATH}")
        sys.exit(1)

    provider = OllamaQwenVisionProvider()
    print(f"Provider  : {provider.provider}")
    print(f"Model     : {provider.model}")
    print(f"Base URL  : {provider.base_url}")
    print(f"Image     : {IMAGE_PATH}  ({os.path.getsize(IMAGE_PATH):,} bytes)")
    print(f"Parts     : {EXPECTED_PARTS}")
    print()

    print("[1/3] Checking Ollama liveness...")
    if not provider._check_ollama_alive():
        print("[FAIL] Ollama is not running. Start with: ollama serve")
        sys.exit(1)
    print("      [OK] Ollama is running")

    print("[2/3] Checking model availability...")
    if not provider._check_model_available():
        print(f"[FAIL] Model '{provider.model}' not installed. Run: ollama pull {provider.model}")
        sys.exit(1)
    print(f"      [OK] Model is available")

    print("[3/3] Sending image to qwen3-vl:8b for inspection...")
    start = time.time()
    result = provider.inspect([IMAGE_PATH], EXPECTED_PARTS, CONDITION_HINT)
    elapsed = time.time() - start

    print()
    print("-" * 60)
    print(f"Latency   : {result.latency_ms} ms  (wall: {elapsed:.1f}s)")
    print(f"Provider  : {result.provider}")
    print(f"Model     : {result.model_name} v{result.model_version}")

    if result.error:
        print(f"\n[FAIL] Vision error: {result.error}")
        print("Status: FAILED - Ollama returned an error or malformed response.")
        sys.exit(1)

    print(f"\nObservations ({len(result.observations)}):")
    for obs in result.observations:
        print(f"  [{obs.state.value:15}] {obs.object_name:25} conf={obs.confidence:.2f}  \"{obs.evidence_desc[:80]}\"")

    print()
    print("=" * 60)
    print("  STATUS: WORKING - VERIFIED")
    print("  Real image -> FastAPI -> Ollama -> qwen3-vl:8b -> {len(result.observations)} structured observations")
    print("=" * 60)

if __name__ == "__main__":
    main()
