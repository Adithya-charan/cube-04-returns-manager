"""
Raw probe: sends the test image to qwen3-vl:8b and prints the raw text response
so we can see what format the model actually produces.
"""
import os, sys, time, base64, requests, json

sys.path.insert(0, ".")
IMAGE_PATH = "fixtures/returns/e2e_test_product.png"
BASE_URL = "http://localhost:11434"
MODEL = "qwen3-vl:8b"

with open(IMAGE_PATH, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

payload = {
    "model": MODEL,
    "messages": [
        {
            "role": "user",
            "content": "Describe what you see in this product return image. List any visible components.",
            "images": [b64],
        }
    ],
    "stream": False,
    "options": {"temperature": 0.1, "num_predict": 512},
}

print(f"Sending to {BASE_URL}/api/chat  model={MODEL} ...")
start = time.time()
resp = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=300)
elapsed = time.time() - start
print(f"Status: {resp.status_code}  elapsed: {elapsed:.1f}s")

try:
    data = resp.json()
    content = data["message"]["content"]
    print(f"\n--- RAW MODEL OUTPUT ({len(content)} chars) ---")
    print(content)
except Exception as e:
    print(f"Parse error: {e}")
    print(resp.text[:2000])
