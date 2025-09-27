"""
Simple document ingest utility for full-text retrieval.

Features:
- Recursively read files from a directory (md, txt, pdf, docx).
- Convert files to plain text using optional dependencies when available.
- Chunk texts into overlapping chunks suitable for retrieval + LLM prompt.
- Persist a simple JSON index: { "documents": [ { "path": "...", "chunks": [ {"id": "...", "text": "..."} ] } ] }

Usage:
- Call `ingest_directory("path/to/docs", out_path="docs_ingest/index.json")`
- Later a retrieval component can load the JSON index and perform simple full-text search.

This utility intentionally avoids heavy dependencies; PDF/DOCX support is optional.
"""

from __future__ import annotations
import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Iterable

# Optional dependencies
try:
    from docx import Document as DocxDocument  # python-docx
except Exception:
    DocxDocument = None

try:
    import PyPDF2  # PyPDF2 for simple PDF text extraction
except Exception:
    PyPDF2 = None


TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}
PDF_EXTENSIONS = {".pdf"}
DOCX_EXTENSIONS = {".docx"}


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            return path.read_text(encoding="latin-1", errors="ignore")
        except Exception:
            return ""


def _read_docx(path: Path) -> str:
    if DocxDocument is None:
        return ""
    try:
        doc = DocxDocument(str(path))
        parts = []
        for p in doc.paragraphs:
            parts.append(p.text)
        return "\n".join(parts)
    except Exception:
        return ""


def _read_pdf(path: Path) -> str:
    if PyPDF2 is None:
        return ""
    try:
        text_parts = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                try:
                    text_parts.append(page.extract_text() or "")
                except Exception:
                    continue
        return "\n".join(text_parts)
    except Exception:
        return ""


def read_file_to_text(path: str) -> str:
    """
    Read a single file to plain text. Supports md, txt, pdf, docx where optional libs exist.
    """
    p = Path(path)
    ext = p.suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return _read_text_file(p)
    if ext in DOCX_EXTENSIONS:
        return _read_docx(p)
    if ext in PDF_EXTENSIONS:
        return _read_pdf(p)
    # Unknown extension -> try plain text read
    return _read_text_file(p)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Chunk text into overlapping chunks.
    """
    if not text:
        return []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    words = text.split()
    if len(words) <= chunk_size:
        return [" ".join(words)]
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start = max(0, end - overlap)
    return chunks


def _chunk_id(doc_path: str, idx: int) -> str:
    # deterministic id for chunk
    h = hashlib.sha1(f"{doc_path}::chunk::{idx}".encode("utf-8")).hexdigest()
    return h


def ingest_directory(
    source_dir: str,
    out_path: str = "mcp-agent/docs_ingest/index.json",
    extensions: Optional[Iterable[str]] = None,
    chunk_size: int = 1000,
    overlap: int = 200,
    ignore_hidden: bool = True,
) -> Dict:
    """
    Walk `source_dir`, read supported files and build an index JSON containing chunks.
    Returns the in-memory index structure and writes it to out_path.

    Index format:
    {
      "documents": [
        {
          "path": "<relative path>",
          "chunks": [
            {"id": "<sha1>", "text": "..."}
          ]
        }, ...
      ]
    }
    """
    base = Path(source_dir)
    if not base.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")
    allowed = set(ext.lower() for ext in (extensions or [".md", ".markdown", ".txt", ".pdf", ".docx"]))
    docs = []
    for root, dirs, files in os.walk(base):
        if ignore_hidden:
            # filter hidden dirs
            dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            if ignore_hidden and fname.startswith("."):
                continue
            p = Path(root) / fname
            if p.suffix.lower() not in allowed:
                continue
            try:
                text = read_file_to_text(str(p))
            except Exception:
                text = ""
            if not text:
                continue
            chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
            chunk_entries = []
            rel = str(p.relative_to(base))
            for i, c in enumerate(chunks):
                chunk_entries.append({"id": _chunk_id(rel, i), "text": c})
            docs.append({"path": rel, "chunks": chunk_entries})
    index = {"documents": docs, "meta": {"source_dir": str(base), "total_documents": len(docs)}}
    # Ensure output directory exists
    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    try:
        out_p.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        raise IOError(f"Failed to write index to {out_path}: {e}")
    return index


def load_index(index_path: str = "mcp-agent/docs_ingest/index.json") -> Dict:
    p = Path(index_path)
    if not p.is_file():
        return {"documents": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"documents": []}


def simple_retrieve(index: Dict, query: str, top_k: int = 5) -> List[Dict]:
    """
    Very simple retrieval: score chunks by number of query tokens present (case-insensitive).
    Returns top_k chunk dicts: {"id":..., "text": ..., "path": ...}
    """
    if not query or not index or "documents" not in index:
        return []
    q = query.lower().split()
    scored = []
    for doc in index["documents"]:
        path = doc.get("path", "")
        for ch in doc.get("chunks", []):
            text = ch.get("text", "")
            if not text:
                continue
            txt_lower = text.lower()
            score = sum(1 for tok in q if tok in txt_lower)
            if score > 0:
                scored.append({"id": ch.get("id"), "text": text, "path": path, "score": score})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# Small CLI convenience
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest documents into simple JSON index for retrieval.")
    parser.add_argument("source", help="Source directory with documents to ingest")
    parser.add_argument("--out", default="mcp-agent/docs_ingest/index.json", help="Output index path")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--overlap", type=int, default=200)
    args = parser.parse_args()
    print(f"Ingesting {args.source} -> {args.out}")
    idx = ingest_directory(args.source, out_path=args.out, chunk_size=args.chunk_size, overlap=args.overlap)
    print(f"Ingested {len(idx.get('documents', []))} documents.")