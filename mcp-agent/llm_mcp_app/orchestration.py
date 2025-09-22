"""
Orchestration logic for MCP Agent.
Handles planning, execution, and agent coordination.
"""

import json
import os
import time
import ast
import asyncio
import inspect
from typing import Optional, Dict, Any, AsyncGenerator
from fastapi import HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

try:
    from mcp_agent.agents.agent import Agent
except ImportError as e:
    import logging
    logging.error(f"Failed to import Agent class: {e}")
    raise

try:
    from .models import ChatCompletionRequest, Message
    from .providers import get_provider
    from .config import logger, LLM_PROVIDER, DEFAULT_MODELS, AGENTS_DIR
except ImportError:
    from models import ChatCompletionRequest, Message
    from providers import get_provider
    from config import logger, LLM_PROVIDER, DEFAULT_MODELS, AGENTS_DIR


def _extract_first_json(text: str):
    """Extract the first JSON object found in the provided text."""
    if not text or not isinstance(text, str):
        return None
    start = text.find('{')
    while start != -1:
        brace = 0
        end = -1
        for i in range(start, len(text)):
            if text[i] == '{':
                brace += 1
            elif text[i] == '}':
                brace -= 1
                if brace == 0:
                    end = i
                    break
        if end != -1:
            candidate = text[start:end+1]
            try:
                return json.loads(candidate)
            except Exception:
                # try next possible '{'
                start = text.find('{', start+1)
                continue
        else:
            break
    return None


def validate_plan_json(plan_obj: Any) -> (bool, str):
    """
    Basic validation for plan JSON structure.
    Expects a dict with top-level "plan": [ { "step": int?, "description": str, "agent": str, "arguments": dict }, ... ]
    Returns (True, "") if valid, otherwise (False, "reason").
    """
    if not isinstance(plan_obj, dict):
        return False, "Plan must be a JSON object"
    plan = plan_obj.get("plan")
    if not isinstance(plan, list):
        return False, "Top-level 'plan' must be an array"
    for idx, step in enumerate(plan, start=1):
        if not isinstance(step, dict):
            return False, f"Step {idx} is not an object"
        if "agent" not in step or not isinstance(step.get("agent"), str) or not step.get("agent"):
            return False, f"Step {idx} missing 'agent' name"
        if "description" in step and not isinstance(step.get("description"), str):
            return False, f"Step {idx} 'description' must be a string"
        if "arguments" in step and not isinstance(step.get("arguments"), dict):
            return False, f"Step {idx} 'arguments' must be an object/dict"
    return True, ""


def plan_obj_to_text(plan_obj: Any) -> str:
    """
    Convert structured plan JSON into the legacy textual plan lines used by execute_plan_stream.
    """
    plan_steps = plan_obj.get("plan", []) if isinstance(plan_obj, dict) else []
    plan_text_lines = []
    for idx, step in enumerate(plan_steps, start=1):
        step_num = step.get("step") or step.get("index") or idx
        desc = step.get("description", "")
        agent_name = step.get("agent", "")
        args = step.get("arguments", {}) or {}
        try:
            args_text = json.dumps(args, ensure_ascii=False)
        except Exception:
            args_text = str(args)
        plan_text_lines.append(f"{step_num}. {desc} - agent: {agent_name}, arguments: {args_text}")
    return "\n".join(plan_text_lines)


async def orchestrate_response(request: ChatCompletionRequest, agents: Dict[str, Agent]) -> JSONResponse:
    """
    Main orchestration logic:
    1. Ask LLM if it can answer directly
    2. If not, create plan using agents
    3. Return plan for user approval
    """
    
    user_message = request.messages[-1].content if request.messages else ""
    
    # Handle quick "show agent" chat commands: if user wrote e.g. "zobraz mi kod agenta X",
    # return agent files immediately without orchestration.
    try:
        show_response = await handle_show_agent_request(request)
        if show_response:
            return show_response
    except Exception as e:
        try:
            logger.error(f"Error in show_agent handler: {e}")
        except Exception:
            pass

    # Create system prompt for decision making
    # NOTE: We now prefer a machine-readable JSON response. If the assistant can
    # answer directly, return a JSON object: {"direct_answer": "..."}.
    # If it needs agents, return a JSON object with a "plan" field:
    # {
    #   "plan": [
    #     {"step": 1, "description": "...", "agent": "codewriter", "arguments": {"task": "..."}},
    #     ...
    #   ]
    # }
    # The assistant MAY also include a short human-friendly summary before/after the JSON,
    # but the JSON object must be parseable by extracting the first JSON object in the text.
    # python
    decision_prompt = """
    You are a helpful AI assistant with access to these agents: {agents_list}
    
    User asks: "{user_message}"
    
    Decide:
    1) If you can answer directly without using agents, respond with valid JSON:
       {"direct_answer": "<your answer here>"}.
    2) If you need to use agents, respond with valid JSON containing a top-level "plan" array:
       {"plan": [{"step": 1, "description": "...", "agent": "<agent_name>", "arguments": {...}}, ...]}.
    
    Available agents and example arguments:
    - finder: {"query": "search terms"}
    - codewriter: {"task": "generate html template for ..."}
    - image_generator: {"prompt": "describe image"}
    - html_parser: {"url": "https://..."}
    
    Rules:
    - Return strictly valid JSON for either the direct_answer or plan case (you may include a short human message, but ensure a valid JSON object appears in the assistant reply).
    - Use clear agent names from the available agents list.
    - Keep plan steps small and ordered.
    
    Only output JSON or JSON plus a short human summary. Do not output ambiguous plain-text plans.
    """.replace("{agents_list}", ", ".join(agents.keys())).replace("{user_message}", user_message)

    # Ask LLM for decision
    current_model = DEFAULT_MODELS.get(LLM_PROVIDER, "gemini-1.5-flash")
    decision_request = ChatCompletionRequest(
        model=current_model,
        messages=[Message(role="user", content=decision_prompt)],
        temperature=0.3
    )
    
    try:
        provider = get_provider(current_model)
        llm_response = await provider.generate(decision_request)
        decision_content = provider._extract_content(llm_response)

        # Debug trace
        try:
            logger.info(f"Orchestration: decision_content (truncated 200 chars): {str(decision_content)[:200]}")
        except Exception:
            logger.info("Orchestration: decision_content (unprintable)")
        try:
            logger.info(f"Orchestration: provider class = {provider.__class__.__name__}")
        except Exception:
            pass
        try:
            logger.info(f"Orchestration: request.stream = {getattr(request, 'stream', False)}")
        except Exception:
            logger.info("Orchestration: could not read request.stream")

        # Helper: create an async SSE generator yielding OpenAI-like chunks
        async def _single_sse(content_str: str):
            # initial content chunk
            chunk = {
                "id": f"chatcmpl-{os.urandom(8).hex()}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{"index": 0, "delta": {"content": content_str}, "finish_reason": None}]
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            # final stop chunk
            final = {
                "id": f"chatcmpl-{os.urandom(8).hex()}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            }
            yield f"data: {json.dumps(final, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        # Try to extract JSON from LLM output (preferred: {"plan": [...]} or {"direct_answer": "..."})
        json_obj = _extract_first_json(decision_content)
        if json_obj and isinstance(json_obj, dict) and "plan" in json_obj:
            plan_obj = json_obj["plan"]
            # Build a human-friendly preview including the JSON plan for confirmation
            try:
                pretty_json = json.dumps(json_obj, ensure_ascii=False, indent=2)
            except Exception:
                pretty_json = str(json_obj)

            plan_response = f"""
Plán byl vytvořen. Níže naleznete strukturovaný plán (JSON):

{pretty_json}

🤔 **Chcete schválit a spustit tento plán?**
Odpovězte 'yes' nebo 'ano' pro spuštění, 'no' nebo 'ne' pro zrušení.
"""

            # If client requested streaming, return SSE with OpenAI-like chunks
            if getattr(request, "stream", False):
                return StreamingResponse(_single_sse(plan_response), media_type="text/event-stream")

            response_content = {
                "id": f"chatcmpl-plan-{os.urandom(8).hex()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": plan_response},
                    "logprobs": None,
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "plan_json": plan_obj
            }
            return JSONResponse(content=response_content)

        # If direct_answer JSON present
        if json_obj and isinstance(json_obj, dict) and "direct_answer" in json_obj:
            answer = json_obj.get("direct_answer", "")

            # Stream if requested
            if getattr(request, "stream", False):
                return StreamingResponse(_single_sse(answer), media_type="text/event-stream")

            response_content = {
                "id": f"chatcmpl-direct-{os.urandom(8).hex()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": answer},
                    "logprobs": None,
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }
            return JSONResponse(content=response_content)

        # Fallback: no valid JSON plan, treat content as direct answer
        # Stream full decision_content if requested (OpenAI-like SSE)
        if getattr(request, "stream", False):
            return StreamingResponse(_single_sse(decision_content), media_type="text/event-stream")

        response_content = {
            "id": f"chatcmpl-direct-{os.urandom(8).hex()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": decision_content},
                "logprobs": None,
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
        return JSONResponse(content=response_content)
        
    except Exception as e:
        logger.error(f"Error in orchestration: {e}")
        raise HTTPException(status_code=500, detail=f"Orchestration error: {str(e)}")


async def handle_plan_execution(request: ChatCompletionRequest, agents: Dict[str, Agent]) -> Optional[JSONResponse]:
    """
    Handles plan confirmation and execution from user.
    """
    if not request.messages or len(request.messages) < 2:
        return None
    
    user_message = request.messages[-1].content.lower().strip()
    previous_message = request.messages[-2].content if len(request.messages) >= 2 else ""
    
    # Check if previous message contained a plan (JSON preferred)
    json_obj = _extract_first_json(previous_message)
    if not (json_obj and isinstance(json_obj, dict) and "plan" in json_obj):
        return None

    if user_message in ['yes', 'ano', 'execute', 'approve', 'ok']:
        # Convert structured plan into textual lines for executor if needed
        plan_steps = json_obj.get("plan", [])
        plan_text_lines = []
        for step in plan_steps:
            step_num = step.get("step") or step.get("index") or (len(plan_text_lines) + 1)
            desc = step.get("description", "")
            agent_name = step.get("agent", "")
            args = step.get("arguments", {})
            args_text = json.dumps(args, ensure_ascii=False)
            plan_text_lines.append(f"{step_num}. {desc} - agent: {agent_name}, arguments: {args_text}")
        plan_text = "\n".join(plan_text_lines)

        # User approved plan - execute it
        return await execute_plan(plan_text, request.model, agents)

    elif user_message in ['no', 'ne', 'cancel', 'reject']:
        # User rejected plan
        response_content = {
            "id": f"chatcmpl-cancel-{os.urandom(8).hex()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "❌ Plan was canceled. You can give me a new task."},
                "logprobs": None,
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
        return JSONResponse(content=response_content)
    
    return None


async def execute_plan(plan_text: str, model: str, agents: Dict[str, Agent]) -> JSONResponse:
    """
    Executes approved plan step by step (synchronous response).
    Kept for backward compatibility — uses the same execution logic as the streaming variant.
    """
    # Reuse streaming executor to collect results
    collected = []
    async for event in execute_plan_stream(plan_text, model, agents):
        # collect human-readable messages when available
        if isinstance(event, dict) and event.get("type") == "step_result":
            collected.append(f"\n🔄 **Step {event.get('step')}:** {event.get('description')}")
            collected.append(f"✅ Result: {event.get('result')}")
        elif isinstance(event, dict) and event.get("type") == "step_error":
            collected.append(f"\n🔄 **Step {event.get('step')}:** {event.get('description')}")
            collected.append(f"❌ Error in step {event.get('step')}: {event.get('error')}")
    collected.insert(0, "✅ **Executing approved plan:**\n")
    collected.append("\n🎉 **Plan completed!**")

    response_content = {
        "id": f"chatcmpl-executed-{os.urandom(8).hex()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "\n".join(collected)},
            "logprobs": None,
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    }
    return JSONResponse(content=response_content)


async def execute_plan_stream(plan_text: str, model: str, agents: Dict[str, Agent]) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream execution of an approved plan.
    Yields events dictionaries for SSE streaming. Events can have types:
      - step_start: {type: "step_start", step, description}
      - step_result: {type: "step_result", step, description, result}
      - step_error: {type: "step_error", step, description, error}
      - finished: {type: "finished"}
    """
    logger.info("Streaming execution of approved plan...")
    # Parse plan lines (retain original simple parser for now)
    plan_lines = [line.strip() for line in plan_text.split('\n') if line.strip() and line.strip()[0].isdigit()]

    for i, line in enumerate(plan_lines, 1):
        description = ""
        try:
            if " - agent: " not in line:
                continue
            description = line.split(" - agent: ")[0]
            agent_part = line.split(" - agent: ")[1]
            if ", arguments: " not in agent_part:
                continue
            agent_name = agent_part.split(", arguments: ")[0]
            args_text = agent_part.split(", arguments: ")[1]

            # Notify start
            yield {"type": "step_start", "step": i, "description": description, "agent": agent_name}

            # Find agent
            agent = agents.get(agent_name)
            if not agent:
                err = f"Agent '{agent_name}' not found"
                yield {"type": "step_error", "step": i, "description": description, "error": err}
                continue

            if not agent.functions:
                err = f"Agent '{agent_name}' has no functions"
                yield {"type": "step_error", "step": i, "description": description, "error": err}
                continue

            # Parse arguments
            try:
                if args_text.startswith('{'):
                    arguments = ast.literal_eval(args_text)
                else:
                    args_clean = args_text.strip('"{}')
                    if agent_name == "image_generator":
                        arguments = {"prompt": args_clean}
                    elif agent_name == "finder":
                        arguments = {"query": args_clean}
                    elif agent_name == "codewriter":
                        arguments = {"task": args_clean}
                    elif agent_name == "html_parser":
                        arguments = {"url": args_clean}
                    else:
                        arguments = {"prompt": args_clean}
            except Exception as parse_error:
                logger.error(f"Error parsing arguments '{args_text}': {parse_error}")
                arguments = {"prompt": args_text.strip('"{}')}

            # Call agent function, support async and sync functions
            agent_function = agent.functions[0]
            try:
                if inspect.iscoroutinefunction(agent_function):
                    result = await agent_function(**arguments)
                else:
                    # If function returns coroutine-like object, await it
                    possible = agent_function(**arguments)
                    if asyncio.iscoroutine(possible):
                        result = await possible
                    else:
                        result = possible
                yield {"type": "step_result", "step": i, "description": description, "result": result}
            except Exception as exec_err:
                logger.error(f"Error executing agent '{agent_name}' step {i}: {exec_err}")
                yield {"type": "step_error", "step": i, "description": description, "error": str(exec_err)}
        except Exception as e:
            logger.error(f"Unexpected error in plan streaming step {i}: {e}")
            yield {"type": "step_error", "step": i, "description": description or f"line:{line}", "error": str(e)}
        # yield control briefly
        await asyncio.sleep(0)

    # Finished
    yield {"type": "finished"}

async def handle_show_agent_request(request: ChatCompletionRequest) -> Optional[JSONResponse]:
    """
    Detect natural-language requests like "zobraz mi kod agenta <name>" and return agent files.
    Returns JSONResponse with assistant-style chat completion containing agent files, or None.
    """
    if not request.messages or not request.messages[-1].content:
        return None
    import re
    last = request.messages[-1].content.strip()
    # Czech and English patterns: "zobraz/ukaz/show ... kod agent <name>"
    m = re.search(r"\b(?:zobraz|ukaz|ukaž|ukažte|show|display)\b.*kod.*agent(?:a)?\s+([A-Za-z0-9_\-]+)", last, re.I)
    if not m:
        return None
    agent_name = m.group(1)
    agent_dir = os.path.join(AGENTS_DIR, agent_name)
    main_py = os.path.join(agent_dir, "main.py")
    yaml_py = os.path.join(agent_dir, "agent.yaml")
    if not os.path.isdir(agent_dir):
        return JSONResponse(status_code=404, content={"detail": f"Agent '{agent_name}' not found"})
    code_text = ""
    yaml_text = ""
    try:
        if os.path.isfile(main_py):
            with open(main_py, "r", encoding="utf-8") as f:
                code_text = f.read()
        if os.path.isfile(yaml_py):
            with open(yaml_py, "r", encoding="utf-8") as f:
                yaml_text = f.read()
    except Exception as e:
        logger.error(f"Error reading agent files for {agent_name}: {e}")
        return JSONResponse(status_code=500, content={"detail": "Failed to read agent files"})
    # Return structured JSON inside assistant content so frontend can render code viewer
    payload = {
        "id": f"chatcmpl-show-{os.urandom(8).hex()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "show_agent": {
                        "name": agent_name,
                        "files": {
                            "main.py": code_text,
                            "agent.yaml": yaml_text
                        }
                    }
                }, ensure_ascii=False)
            },
            "finish_reason": "stop"
        }],
    }
    return JSONResponse(content=payload)


async def handle_agent_call(request: ChatCompletionRequest, agents: Dict[str, Agent]) -> Optional[JSONResponse]:
    """
    Handle direct agent calls (legacy support).

    Supports async agent functions and coroutine results returned by sync functions.
    Expects last user message to be a JSON with structure:
    {"tool_call": {"name": "<agent_name>", "arguments": {...}}}
    """
    if not request.messages or request.messages[-1].role != "user":
        return None

    last_message_content = request.messages[-1].content
    try:
        tool_call_data = json.loads(last_message_content)
        if not (isinstance(tool_call_data, dict) and "tool_call" in tool_call_data):
            return None

        tool_call = tool_call_data["tool_call"]
        agent_name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})

        agent = agents.get(agent_name)
        if not agent:
            logger.warning(f"Agent '{agent_name}' not found.")
            return None

        logger.info(f"Executing agent: {agent_name} with arguments: {arguments}")

        if not agent.functions:
            raise HTTPException(status_code=500, detail=f"Agent '{agent_name}' has no functions.")

        agent_function = agent.functions[0]

        # Execute agent function with support for async functions and coroutine results
        try:
            if inspect.iscoroutinefunction(agent_function):
                result = await agent_function(**arguments)
            else:
                possible = agent_function(**arguments)
                if asyncio.iscoroutine(possible):
                    result = await possible
                else:
                    result = possible
        except Exception as exec_err:
            logger.error(f"Error executing agent '{agent_name}': {exec_err}")
            raise HTTPException(status_code=500, detail=f"Error during agent execution: {str(exec_err)}")

        response_content = {
            "id": f"chatcmpl-agent-{os.urandom(8).hex()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": f"agent/{agent_name}",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": str(result)},
                "logprobs": None,
                "finish_reason": "tool_calls"
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
        return JSONResponse(content=response_content)

    except json.JSONDecodeError:
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing agent call: {e}")
        raise HTTPException(status_code=500, detail=f"Error during agent execution: {str(e)}")
