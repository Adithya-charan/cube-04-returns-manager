import json
import csv
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

print("--- Testing /health ---")
health_resp = client.get("/health")
print(f"Status: {health_resp.status_code}")
print(f"Response: {health_resp.json()}")

print("\n--- Testing Ingestion with real row from returns_sample.csv ---")
with open("data/returns_sample.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    row = next(reader)

ingest_resp = client.post("/agent", json=row)
print(f"Status: {ingest_resp.status_code}")
print(f"Response:\n{json.dumps(ingest_resp.json(), indent=2)}")
