import os
import sys
import json
import pytest

os.environ["ENVIRONMENT"] = "local"
os.environ["RATE_LIMIT"] = "2/minute"
os.environ["REDIS_URI"] = "redis://localhost:6379"

sys.path.insert(0, "../../src/ersilia_pack")

@pytest.fixture
def create_information_file():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_file_path = os.path.normpath(os.path.join(current_dir, "../../src/ersilia_pack/information.json"))
    
    txt_file_path = os.path.join(current_dir, "info.txt")
    
    with open(txt_file_path, "r") as txt_file:
        data = json.load(txt_file)
    
    with open(target_file_path, "w") as f:
        json.dump(data, f, indent=4)
    
    yield
    
    if os.path.exists(target_file_path):
        os.remove(target_file_path)

def test_rate_limiting(create_information_file):

    from fastapi.testclient import TestClient
    from src.ersilia_pack.templates.app import app

    client = TestClient(app)

    resp_one = client.get("/card")
    assert resp_one.status_code == 200, f"Expected 200, got {resp_one.status_code}"

    resp_two = client.get("/card")
    assert resp_two.status_code == 200, f"Expected 200, got {resp_two.status_code}"

    resp_three = client.get("/card")
    assert resp_three.status_code == 429, f"Expected 429, got {resp_three.status_code}"
    assert "Retry-After" in resp_three.headers, "Missing Retry-After header"
    