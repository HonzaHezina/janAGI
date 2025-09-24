"""
Planner utilities extracted from orchestration.py.

Contains JSON extraction, plan validation, plan -> text transformation,
and building the decision prompt / human preview used by the orchestrator.
"""

import json
from typing import Any, Dict, List


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


def build_decision_prompt(agents_list: List[str], user_message: str) -> str:
    """
    Build the decision prompt used to ask the LLM whether to answer directly or produce a plan.
    """
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
    """.replace("{agents_list}", ", ".join(agents_list)).replace("{user_message}", user_message)
    return decision_prompt


def format_plan_preview(plan_obj: Any) -> str:
    """
    Create a human-friendly preview string for a plan (used for confirmation).
    """
    try:
        pretty_json = json.dumps(plan_obj if isinstance(plan_obj, dict) else {"plan": plan_obj}, ensure_ascii=False, indent=2)
    except Exception:
        pretty_json = str(plan_obj)

    plan_response = f"""
Plán byl vytvořen. Níže naleznete strukturovaný plán (JSON):

{pretty_json}

🤔 **Chcete schválit a spustit tento plán?**
Odpovězte 'yes' nebo 'ano' pro spuštění, 'no' nebo 'ne' pro zrušení.
"""
    return plan_response