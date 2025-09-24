"""
Main FastAPI application for MCP Agent Orchestrator.
Simplified version with modular imports.
"""

import time
import json
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
 
try:
    # Try relative imports first (when run as module)
    from .config import logger, LLM_PROVIDER, DEFAULT_MODELS, AGENTS_DIR
    from .models import ChatCompletionRequest
    from .agents import load_all_agents
    from .orchestration import (
        orchestrate_response,
        handle_plan_execution,
        handle_agent_call,
        execute_plan_stream,
    )
    from . import __version__, __title__
except ImportError:
    # Fall back to absolute imports (when run as script)
    from config import logger, LLM_PROVIDER, DEFAULT_MODELS, AGENTS_DIR
    from models import ChatCompletionRequest
    from agents import load_all_agents
    from orchestration import (
        orchestrate_response,
        handle_plan_execution,
        handle_agent_call,
        execute_plan_stream,
    )
    from __init__ import __version__, __title__


# --- FastAPI App Setup ---
app = FastAPI(
    title=__title__,
    description="Routes requests to agents or a default LLM provider.",
    version=__version__
)

# --- Load Agents ---
AGENTS = load_all_agents()
logger.info(f"Successfully loaded agents: {list(AGENTS.keys())}")


# --- API Endpoints ---
@app.get("/v1/models")
async def get_models():
    """Get available models (agents + LLM models)."""
    agent_models = [{"id": name, "object": "model", "owned_by": "agent"} for name in AGENTS.keys()]
    
    # Přidáme různé LLM modely podle konfigurace
    llm_models = []
    current_model = DEFAULT_MODELS.get(LLM_PROVIDER, "gemini-1.5-flash")
    
    if LLM_PROVIDER == "gemini":
        llm_models = [
            {"id": "gemini-1.5-flash", "object": "model", "owned_by": "google"},
            {"id": "gemini-1.5-pro", "object": "model", "owned_by": "google"},
        ]
    elif LLM_PROVIDER == "huggingface":
        llm_models = [
            {"id": "microsoft/DialoGPT-medium", "object": "model", "owned_by": "huggingface"},
            {"id": "microsoft/DialoGPT-large", "object": "model", "owned_by": "huggingface"},
            {"id": "facebook/blenderbot-400M-distill", "object": "model", "owned_by": "huggingface"},
        ]
    elif LLM_PROVIDER == "openai":
        llm_models = [
            {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "openai"},
            {"id": "gpt-4", "object": "model", "owned_by": "openai"},
        ]
    
    return JSONResponse(content={"data": agent_models + llm_models, "object": "list"})
    
# --- Agents management endpoints ---
from fastapi import Request, Body
from pathlib import Path

@app.get("/v1/agents")
async def list_agents():
    """Return list of currently loaded agents."""
    return JSONResponse(content={"agents": list(AGENTS.keys())})

@app.get("/v1/agents/{agent_name}/code")
async def get_agent_code(agent_name: str):
    """Return the source code of the agent's main.py if available."""
    agent_path = Path(AGENTS_DIR) / agent_name / "main.py"
    if not agent_path.is_file():
        return JSONResponse(status_code=404, content={"detail": "Agent or code not found"})
    try:
        return JSONResponse(content={"name": agent_name, "code": agent_path.read_text(encoding='utf-8')})
    except Exception as e:
        logger.error(f"Error reading agent code for {agent_name}: {e}")
        return JSONResponse(status_code=500, content={"detail": "Failed to read agent code"})

@app.put("/v1/agents/{agent_name}/code")
async def put_agent_code(agent_name: str, payload: dict = Body(...)):
    """Replace agent code and reload agents. Payload: { "code": "..." }"""
    code = payload.get("code")
    if code is None:
        return JSONResponse(status_code=400, content={"detail": "Missing 'code' in body"})
    agent_dir = Path(AGENTS_DIR) / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_main = agent_dir / "main.py"
    try:
        agent_main.write_text(code, encoding='utf-8')
    except Exception as e:
        logger.error(f"Failed to write code for agent {agent_name}: {e}")
        return JSONResponse(status_code=500, content={"detail": "Failed to write agent code"})
    # Reload agents
    global AGENTS
    AGENTS = load_all_agents()
    logger.info(f"Reloaded agents after update: {list(AGENTS.keys())}")
    return JSONResponse(content={"detail": "Agent code updated and agents reloaded", "agents": list(AGENTS.keys())})

@app.post("/v1/agents/reload")
async def reload_agents():
    """Force reload of all agents from disk."""
    global AGENTS
    AGENTS = load_all_agents()
    logger.info(f"Agents reloaded: {list(AGENTS.keys())}")
    return JSONResponse(content={"detail": "Agents reloaded", "agents": list(AGENTS.keys())})

# --- Plan execution streaming endpoint ---
from fastapi.responses import StreamingResponse
import asyncio

@app.post("/v1/plan/stream")
async def plan_stream(request: Request):
    """
    Stream execution of a plan. Expect JSON body with:
    { "plan": "<plan_text>", "model": "mcp-orchestrator" }
    Streams Server-Sent Events with 'data: <json>' frames.
    """
    body = await request.json()
    plan_text = body.get("plan")
    model = body.get("model", "mcp-orchestrator")
    if not plan_text:
        return JSONResponse(status_code=400, content={"detail": "Missing 'plan' in body"})

    async def event_generator():
        try:
            # Delegate to orchestration streaming executor
            try:
                from .orchestration import execute_plan_stream
            except ImportError:
                from orchestration import execute_plan_stream

            async for chunk in execute_plan_stream(plan_text, model, AGENTS):
                # Each chunk is expected to be a dict or string; ensure it's JSON string
                if isinstance(chunk, dict):
                    data = json.dumps(chunk, ensure_ascii=False)
                else:
                    data = str(chunk)
                yield f"data: {data}\n\n"
                await asyncio.sleep(0)  # yield control
        except Exception as e:
            logger.error(f"Error in plan_stream generator: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
@app.post("/v1/plan/preview")
async def plan_preview(request: Request):
    """
    Return a human-friendly preview for a given plan JSON.
    Expects body: { "plan": <plan_object_or_string> }
    """
    body = await request.json()
    plan = body.get("plan")
    if not plan:
        return JSONResponse(status_code=400, content={"detail": "Missing 'plan' in body"})
    try:
        # Normalize plan object if it's a JSON string
        if isinstance(plan, str):
            try:
                plan_obj = json.loads(plan)
            except Exception:
                # treat as textual plan (legacy) — return as-is in preview
                return JSONResponse(content={"preview": str(plan)})
        else:
            plan_obj = plan
        try:
            from .planner import format_plan_preview
        except ImportError:
            from planner import format_plan_preview
        preview = format_plan_preview(plan_obj)
        return JSONResponse(content={"preview": preview})
    except Exception as e:
        logger.error(f"Error building plan preview: {e}")
        return JSONResponse(status_code=500, content={"detail": "Failed to build plan preview"})


@app.post("/v1/docs/ingest")
async def docs_ingest(payload: dict = Body(...)):
    """
    Ingest documents from a local directory into a simple JSON index.
    Payload: { "path": "<source_dir>", "out": "<optional output path>" }
    """
    source = payload.get("path")
    out = payload.get("out", "mcp-agent/docs_ingest/index.json")
    if not source:
        return JSONResponse(status_code=400, content={"detail": "Missing 'path' in body"})
    try:
        try:
            from .docs_ingest.ingest import ingest_directory
        except ImportError:
            from docs_ingest.ingest import ingest_directory
        idx = ingest_directory(source, out_path=out)
        return JSONResponse(content={"ingested": idx.get("meta", {}).get("total_documents", 0), "out": out})
    except Exception as e:
        logger.error(f"Error during docs ingest: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/v1/docs/query")
async def docs_query(payload: dict = Body(...)):
    """
    Query the JSON index for relevant document excerpts.
    Payload: { "query": "<user query>", "index_path": "<optional index path>", "top_k": 5 }
    """
    query = payload.get("query")
    index_path = payload.get("index_path", "mcp-agent/docs_ingest/index.json")
    top_k = int(payload.get("top_k", 5))
    if not query:
        return JSONResponse(status_code=400, content={"detail": "Missing 'query' in body"})
    try:
        try:
            from .docs_ingest.ingest import load_index, simple_retrieve
        except ImportError:
            from docs_ingest.ingest import load_index, simple_retrieve
        index = load_index(index_path)
        results = simple_retrieve(index, query, top_k=top_k)
        return JSONResponse(content={"query": query, "results": results})
    except Exception as e:
        logger.error(f"Error during docs query: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    try:
        logger.info(f"Chat request received with model: {request.model}")
        
        # Special handling for mcp-orchestrator model - always use orchestration
        if request.model == "mcp-orchestrator":
            logger.info("Using orchestration workflow")
            try:
                from .orchestration import orchestrate_response
            except ImportError:
                from orchestration import orchestrate_response
            
            # Use orchestration workflow with agents
            return await orchestrate_response(request, AGENTS)
        
        # For other models, use direct provider
        logger.info(f"Using direct provider for model: {request.model}")
        from providers import get_provider
        provider = get_provider(request.model)
        response = await provider.chat(request.messages, request.max_tokens, request.temperature)
        
        return {
            "id": f"chatcmpl-{request.model}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": sum(len(msg["content"]) for msg in request.messages) // 4,
                "completion_tokens": len(response) // 4,
                "total_tokens": (sum(len(msg["content"]) for msg in request.messages) + len(response)) // 4
            }
        }
    except Exception as e:
        from fastapi import HTTPException
        logger.error(f"Error in chat_completions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server at http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)