"""End-to-end API tests using FastAPI TestClient.

conftest.py patches the key store so all tests run in demo mode.
"""
from fastapi.testclient import TestClient
from src.api.server import app

client = TestClient(app)


def test_health_endpoint():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_report_demo():
    r = client.post("/api/report", json={"subject": "t", "depth": "基础"})
    assert r.status_code == 200
    assert "markdown" in r.json()


def test_outline_demo():
    r = client.post("/api/outline", json={"subject": "t"})
    assert r.status_code == 200
    assert "markdown" in r.json()


def test_thesis_demo():
    r = client.post("/api/thesis", json={"blockTitle": "t", "prompt": "p"})
    assert r.status_code == 200
    assert "markdown" in r.json()


def test_review_demo():
    r = client.post("/api/literature-review", json={"keyword": "AI"})
    assert r.status_code == 200
    assert "markdown" in r.json()


def test_assistant_demo():
    r = client.post("/api/assistant", json={"prompt": "hello"})
    assert r.status_code == 200
    assert "markdown" in r.json()


def test_skills_list():
    r = client.get("/api/skills")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_providers_list():
    r = client.get("/api/providers")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
