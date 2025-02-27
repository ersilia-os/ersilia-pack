import importlib
import pytest
from fastapi.testclient import TestClient
from _pytest.monkeypatch import MonkeyPatch

@pytest.fixture(scope="module", autouse=True)
def prod_env():
    mp = MonkeyPatch()
    mp.setenv("ENVIRONMENT", "prod")
    mp.setenv("ALLOWED_ORIGINS", "http://example.com, http://another.com")
    
    from src.ersilia_pack.templates import app
    importlib.reload(app)
    
    yield app
    
    mp.undo()  

def test_cors_allowed_origin(prod_env):
    client = TestClient(prod_env.app)
    headers = {"Origin": "http://example.com"}
    response = client.get("/", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://example.com"

def test_cors_disallowed_origin(prod_env):
    client = TestClient(prod_env.app)
    headers = {"Origin": "http://notallowed.com"}
    response = client.get("/", headers=headers)
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers

def test_cors_preflight_allowed_origin(prod_env):
    client = TestClient(prod_env.app)
    headers = {
        "Origin": "http://example.com",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://example.com"