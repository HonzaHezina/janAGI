from pathlib import Path
from importlib import util
import pytest
from fastapi.testclient import TestClient
import json

ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "llm_mcp_app" / "main.py"

def _load_main_module():
    spec = util.spec_from_file_location("llm_mcp_app.main", str(MAIN_PATH))
    module = util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        pytest.skip(f"Could not import llm_mcp_app.main: {e}")
    return module

def test_docs_ingest_and_query_endpoints(tmp_path):
    module = _load_main_module()
    client = TestClient(module.app)

    # prepare docs
    src = tmp_path / "docs"
    src.mkdir()
    f1 = src / "one.md"
    f1.write_text("This is onboarding documentation. Contact: onboarding@example.com", encoding="utf-8")
    index_file = tmp_path / "index.json"

    # ingest
    resp = client.post("/v1/docs/ingest", json={"path": str(src), "out": str(index_file)})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "ingested" in data
    assert data.get("out") == str(index_file)

    # query
    resp2 = client.post("/v1/docs/query", json={"query": "onboarding contact", "index_path": str(index_file), "top_k": 5})
    assert resp2.status_code == 200, resp2.text
    qdata = resp2.json()
    assert qdata.get("query") == "onboarding contact"
    assert isinstance(qdata.get("results"), list)
    assert len(qdata["results"]) >= 1