import os, sys
os.environ["ENVIRONMENT"] = "prod"
os.environ["RATE_LIMIT"] = "2/minute"
os.environ["REDIS_URI"] = "redis://localhost:6379"

sys.path.insert(0, "../../src/ersilia_pack")

from fastapi.testclient import TestClient

from src.ersilia_pack.templates.app import app




client = TestClient(app)


def test_rate_limiting():
  resp_one = client.get("/card")
  assert resp_one.status_code == 200, f"Expected 200, got {resp_one.status_code}"

  resp_two = client.get("/card")
  assert resp_two.status_code == 200, f"Expected 200, got {resp_two.status_code}"

  resp_three = client.get("/card")
  assert resp_three.status_code == 429, f"Expected 429, got {resp_three.status_code}"
  assert "Retry-After" in resp_three.headers, "Missing Retry-After header"
