"""
Orchestration logic for MCP Agent.
Handles planning, execution, and agent coordination.
"""

import json
import os
import time
import ast
from typing import Optional, Dict
from fastapi import HTTPException
from fastapi.responses import JSONResponse

try:
    from mcp_agent.agents.agent import Agent
except ImportError as e:
    import logging
    logging.error(f"Failed to import Agent class: {e}")
    raise

try:
    from .models import ChatCompletionRequest, Message
    from .providers import get_provider
    from .config import logger, LLM_PROVIDER, DEFAULT_MODELS
except ImportError:
    from models import ChatCompletionRequest, Message
    from providers import get_provider
    from config import logger, LLM_PROVIDER, DEFAULT_MODELS


async def orchestrate_response(request: ChatCompletionRequest, agents: Dict[str, Agent]) -> JSONResponse:
    """
    Main orchestration logic:
    1. Ask LLM if it can answer directly
    2. If not, create plan using agents
    3. Return plan for user approval
    """
    
    user_message = request.messages[-1].content if request.messages else ""
    
    # Create system prompt for decision making
    decision_prompt = f"""
You are a helpful AI assistant with access to these agents:
{', '.join(agents.keys())}

User asks: "{user_message}"

Decide:
1. If you can answer directly without agents, respond normally.
2. If you need agents, create a plan in format:

PLAN:
1. [step description] - agent: [agent_name], arguments: [arguments]
2. [step description] - agent: [agent_name], arguments: [arguments]
...

Available agents:
- finder: file search (arguments: query)
- codewriter: code generation (arguments: task)
- image_generator: image generation (arguments: prompt)
- html_parser: web scraping (arguments: url)

Answer either:
- Directly to the question (without word PLAN)
- Or create PLAN: with steps
"""

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
        
        # Check if LLM created a plan
        if "PLAN:" in decision_content:
            # LLM created plan - return for approval
            plan_response = f"""
{decision_content}

🤔 **Do you want to approve and execute this plan?**
Answer 'yes' to execute or 'no' to cancel.
"""
            
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
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }
            return JSONResponse(content=response_content)
        
        else:
            # LLM answered directly - return response with correct model name
            response_content = {
                "id": f"chatcmpl-direct-{os.urandom(8).hex()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,  # Keep original model name (mcp-orchestrator)
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
    
    # Check if previous message contained a plan
    if "PLAN:" not in previous_message or "Do you want to approve" not in previous_message:
        return None
    
    if user_message in ['yes', 'ano', 'execute', 'approve', 'ok']:
        # User approved plan - execute it
        return await execute_plan(previous_message, request.model, agents)
    
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
    Executes approved plan step by step.
    """
    logger.info("Executing approved plan...")
    
    results = ["✅ **Executing approved plan:**\n"]
    
    # Parse plan
    plan_lines = [line.strip() for line in plan_text.split('\n') if line.strip() and line.strip()[0].isdigit()]
    
    for i, line in enumerate(plan_lines, 1):
        try:
            # Parse plan line
            # Format: "1. description - agent: name, arguments: {args}"
            if " - agent: " not in line:
                continue
                
            description = line.split(" - agent: ")[0]
            agent_part = line.split(" - agent: ")[1]
            
            if ", arguments: " not in agent_part:
                continue
                
            agent_name = agent_part.split(", arguments: ")[0]
            args_text = agent_part.split(", arguments: ")[1]
            
            results.append(f"\n🔄 **Step {i}:** {description}")
            
            # Find agent
            agent = agents.get(agent_name)
            if not agent:
                results.append(f"❌ Agent '{agent_name}' not found")
                continue
            
            # Execute agent
            if not agent.functions:
                results.append(f"❌ Agent '{agent_name}' has no functions")
                continue
            
            # Parse arguments according to agent
            try:
                # If arguments are in JSON format
                if args_text.startswith('{'):
                    arguments = ast.literal_eval(args_text)
                else:
                    # Otherwise use correct argument based on agent
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
            
            agent_function = agent.functions[0]
            result = agent_function(**arguments)
            
            results.append(f"✅ Result: {result}")
            
        except Exception as e:
            logger.error(f"Error executing plan step {i}: {e}")
            results.append(f"❌ Error in step {i}: {str(e)}")
    
    results.append("\n🎉 **Plan completed!**")
    
    response_content = {
        "id": f"chatcmpl-executed-{os.urandom(8).hex()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "\n".join(results)},
            "logprobs": None,
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    }
    return JSONResponse(content=response_content)


async def handle_agent_call(request: ChatCompletionRequest, agents: Dict[str, Agent]) -> Optional[JSONResponse]:
    """
    Handle direct agent calls (legacy support).
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
        result = agent_function(**arguments)

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
    except Exception as e:
        logger.error(f"Error executing agent call: {e}")
        raise HTTPException(status_code=500, detail=f"Error during agent execution: {str(e)}")
