from pathlib import Path
from importlib import util
import json
import pytest

# Dynamically load ingest module from repository path to avoid package import issues
ROOT = Path(__file__).resolve().parents[1]  # points to mcp-agent
INGEST_PATH = ROOT / "docs_ingest" / "ingest.py"
spec = util.spec_from_file_location("docs_ingest.ingest", str(INGEST_PATH))
ingest_mod = util.module_from_spec(spec)
spec.loader.exec_module(ingest_mod)

chunk_text = ingest_mod.chunk_text
ingest_directory = ingest_mod.ingest_directory
load_index = ingest_mod.load_index
simple_retrieve = ingest_mod.simple_retrieve


def test_chunk_text_basic():
    text = "word " * 1500
    chunks = chunk_text(text, chunk_size=1000, overlap=200)
    assert isinstance(chunks, list)
    # With 1500 words and chunk_size 1000, should produce at least 2 chunks
    assert len(chunks) >= 2
    # Overlap means some words repeat at chunk boundaries
    assert all(isinstance(c, str) and c for c in chunks)


def test_ingest_directory_and_load(tmp_path):
    # create simple source dir with two files
    src = tmp_path / "docs"
    src.mkdir()
    f1 = src / "one.md"
    f1.write_text("This is onboarding documentation. Please read onboarding instructions.", encoding="utf-8")
    f2 = src / "two.txt"
    f2.write_text("Misc content without the magic word.", encoding="utf-8")

    out = tmp_path / "index.json"
    idx = ingest_directory(str(src), out_path=str(out), chunk_size=50, overlap=10)
    assert "documents" in idx
    # one.md should be present because it contains text
    docs = {d["path"]: d for d in idx["documents"]}
    assert "one.md" in docs
    assert isinstance(idx.get("meta", {}).get("total_documents"), int)
    # file wrote to disk
    loaded = load_index(str(out))
    assert loaded.get("documents") and isinstance(loaded["documents"], list)


def test_simple_retrieve_scores(tmp_path):
    # Build an index structure inline
    index = {
        "documents": [
            {"path": "a.md", "chunks": [{"id": "c1", "text": "This onboarding text mentions getting started."}]},
            {"path": "b.md", "chunks": [{"id": "c2", "text": "Other content unrelated."}]}
        ]
    }
    results = simple_retrieve(index, "onboarding getting", top_k=5)
    assert isinstance(results, list)
    assert len(results) >= 1
    # top result should contain the onboarding phrase
    assert any("onboarding" in r["text"].lower() for r in results)