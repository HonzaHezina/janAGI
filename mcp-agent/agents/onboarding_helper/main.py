from typing import Dict, Optional, List
import asyncio
import json
from pathlib import Path

# Per-agent runner / provider fallbacks (same pattern as other agents)
try:
    from mcp_agent.llm_mcp_app.providers import get_provider
    from mcp_agent.llm_mcp_app.models import Message
    from mcp_agent.agents.agent import Agent
    from mcp_agent.docs_ingest.ingest import load_index, ingest_directory, simple_retrieve
except ImportError:
    from llm_mcp_app.providers import get_provider  # type: ignore
    from llm_mcp_app.models import Message  # type: ignore
    from mcp_agent.agents.agent import Agent  # type: ignore
    from docs_ingest.ingest import load_index, ingest_directory, simple_retrieve  # type: ignore


DEFAULT_INDEX_PATH = "mcp-agent/docs_ingest/index.json"


def _build_prompt(query: str, contexts: List[Dict], max_context_chars: int = 2500) -> str:
    """
    Build a prompt containing the most relevant contexts and the user query.
    """
    intro = (
        "You are an internal onboarding assistant. Use the provided document excerpts to answer the user's question precisely. "
        "If the answer is not contained in the excerpts, say you don't know and suggest where to look."
    )
    parts = [intro, "\n---\nRelevant excerpts:\n"]
    total = 0
    for c in contexts:
        text = c.get("text", "")
        path = c.get("path", "")
        excerpt = f"[from {path}]\n{text}\n"
        if total + len(excerpt) > max_context_chars:
            break
        parts.append(excerpt)
        total += len(excerpt)
    parts.append("\nUser question:\n" + query + "\n")
    parts.append("\nAnswer concisely, mention source paths in brackets when appropriate.")
    return "\n".join(parts)


def answer(query: str, agent_config: Optional[Dict] = None) -> str:
    """
    Retrieve top chunks for `query` and ask the configured provider for an answer.
    Synchronous wrapper (agents in this repo expose sync functions).
    """
    # Load index
    index_path = agent_config.get("index_path") if (agent_config and isinstance(agent_config, dict) and agent_config.get("index_path")) else DEFAULT_INDEX_PATH
    index = load_index(index_path)
    if not index or not index.get("documents"):
        return "No documents indexed. Use add_documents(path) to index a documents directory."

    # Retrieve top chunks
    top = simple_retrieve(index, query, top_k=5)
    if not top:
        return "No relevant documents found for your query."

    # Build prompt and call provider
    prompt = _build_prompt(query, top)
    model = None
    provider_override = None
    if agent_config and isinstance(agent_config, dict):
        model = agent_config.get("model")
        provider_override = agent_config.get("provider")

    provider = get_provider(model, provider_override)
    messages = [Message(role="user", content=prompt)]

    try:
        # provider.chat is async
        resp = asyncio.run(provider.chat(messages, max_tokens=1024, temperature=0.2))
        if isinstance(resp, dict):
            return resp.get("result") or resp.get("generated_text") or str(resp)
        return str(resp)
    except Exception as e:
        return f"[ERROR] Failed to get answer: {e}"


def add_documents(path: str, agent_config: Optional[Dict] = None) -> str:
    """
    Ingest documents from `path` into the default JSON index.
    Returns a JSON string with ingestion summary.
    """
    out_path = agent_config.get("index_path") if (agent_config and isinstance(agent_config, dict) and agent_config.get("index_path")) else DEFAULT_INDEX_PATH
    try:
        idx = ingest_directory(path, out_path=out_path)
        return json.dumps({"ingested": idx.get("meta", {}).get("total_documents", 0), "out": out_path})
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_agent(agent_config: Optional[Dict] = None) -> Agent:
    """
    Returns the onboarding_helper agent exposing:
    - answer(query: str) -> str
    - add_documents(path: str) -> str
    """
    def _answer(q: str) -> str:
        return answer(q, agent_config)

    def _add(path: str) -> str:
        return add_documents(path, agent_config)

    instruction = (
        "Agent for answering questions from internal documentation. "
        "Use add_documents(path) to index a directory of docs, then use answer(query) to query."
    )

    return Agent(name="onboarding_helper", instruction=instruction, functions=[_answer, _add])


if __name__ == "__main__":
    a = get_agent()
    print("Agent created:", a.name)
    print("Instruction:", a.instruction)
    # Demo: not executed here, requires local files and optional libs