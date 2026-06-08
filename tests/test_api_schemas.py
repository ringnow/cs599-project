"""Test API schemas."""
from src.api.schemas import ReportRequest, ApiResponse

def test_report_request_defaults():
    r = ReportRequest(subject="test")
    assert r.subject == "test"
    assert r.depth == "详细"
    assert r.skill_override == ""

def test_api_response_steps():
    r = ApiResponse(logs=["ok"], markdown="# hello", steps=[{"step": 1}])
    assert len(r.steps) == 1
    assert r.steps[0]["step"] == 1
