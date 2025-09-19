"""
Main FastAPI application for MCP Agent Orchestrator.
Simplified version with modular imports.
"""

import time
from fastapi import FastAPI
from fastapi.responses import JSONResponse

try:
    # Try relative imports first (when run as module)
    from .config import logger, LLM_PROVIDER, DEFAULT_MODELS
    from .models import ChatCompletionRequest
    from .agents import load_all_agents
    from .orchestration import orchestrate_response, handle_plan_execution, handle_agent_call
    from . import __version__, __title__
except ImportError:
    # Fall back to absolute imports (when run as script)
    from config import logger, LLM_PROVIDER, DEFAULT_MODELS
    from models import ChatCompletionRequest
    from agents import load_all_agents
    from orchestration import orchestrate_response, handle_plan_execution, handle_agent_call
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