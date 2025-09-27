import pytest
from mcp_agent.llm_mcp_app.planner import _extract_first_json, validate_plan_json, plan_obj_to_text

def test_extract_first_json_simple():
    text = 'Intro text {"plan":[{"step":1,"description":"do","agent":"finder","arguments":{}}]} tail'
    obj = _extract_first_json(text)
    assert isinstance(obj, dict)
    assert "plan" in obj

def test_validate_plan_json_good():
    plan_obj = {"plan": [{"step": 1, "description": "do it", "agent": "finder", "arguments": {}}]}
    valid, reason = validate_plan_json(plan_obj)
    assert valid is True

def test_validate_plan_json_bad():
    invalid = {"not_plan": []}
    valid, reason = validate_plan_json(invalid)
    assert valid is False

def test_plan_obj_to_text_basic():
    plan_obj = {"plan": [{"step": 1, "description": "Fetch data", "agent": "finder", "arguments": {"query": "report"}}]}
    text = plan_obj_to_text(plan_obj)
    assert "agent: finder" in text
    assert "arguments" in text