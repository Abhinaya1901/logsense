import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    return TestClient(main.app)


def explain(client, log, context="odata"):
    response = client.post("/api/explain", json={"log": log, "context": context})
    assert response.status_code == 200
    return response.json()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "llm_enabled": False}


def test_invalid_property_filter(client):
    result = explain(client, "HTTP 400 Bad Request\nMessage: No property 'Price' exists in type 'NorthwindModel.Product'")
    assert "property" in result["summary"].lower()
    assert result["source"] == "offline SAP rule base"


def test_missing_entity_set(client):
    result = explain(client, "HTTP 404 Not Found\nMessage: Resource not found for the segment 'ProductCatalog'.")
    assert "/IWFND/MAINT_SERVICE" in " ".join(result["fix_steps"])


def test_abap_dump(client):
    result = explain(client, "Runtime Errors COMPUTE_INT_ZERODIVIDE\nException CX_SY_ZERODIVIDE", context="abap")
    assert result["severity"] == "High"
    assert "ST22" in result["where_to_look"]


def test_unknown_log_gets_generic_answer(client):
    result = explain(client, "something odd happened")
    assert result["severity"] == "Low"
    assert len(result["fix_steps"]) >= 2


def test_empty_log_rejected(client):
    assert client.post("/api/explain", json={"log": ""}).status_code == 422


def test_secrets_are_masked():
    masked = main.mask_secrets("Authorization: Basic dXNlcjpwYXNz\npassword=hunter2\nX-CSRF-Token: abc123")
    assert "dXNlcjpwYXNz" not in masked
    assert "hunter2" not in masked
    assert "abc123" not in masked


def test_llm_failure_falls_back(monkeypatch, client):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    def boom(*args, **kwargs):
        raise main.httpx.ConnectError("offline")

    monkeypatch.setattr(main.httpx, "post", boom)
    result = explain(client, "CX_SY_ITAB_LINE_NOT_FOUND", context="abap")
    assert result["source"].startswith("offline SAP rule base (LLM unavailable")
