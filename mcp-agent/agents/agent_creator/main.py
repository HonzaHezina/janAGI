from mcp_agent.agents.agent import Agent
from typing import Dict, Optional
import os
import asyncio
import re
import json

# Prefer per-agent runner and allow agent-specific model/provider via agent_config.
# Keep a fallback import path for running from repository root or examples.
try:
    from mcp_agent.llm_mcp_app.agent_runner import AgentRunner
    from mcp_agent.llm_mcp_app.providers import get_provider
    from mcp_agent.llm_mcp_app.models import Message
except ImportError:
    from llm_mcp_app.agent_runner import AgentRunner  # type: ignore
    from llm_mcp_app.providers import get_provider  # type: ignore
    from llm_mcp_app.models import Message  # type: ignore

REQUIRED_KEYS = ["name", "description", "model", "provider", "prompt_template", "permissions", "timeout", "entrypoint"]
MAX_NAME_LENGTH = 50
NAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")


def _is_valid_name(name: str) -> bool:
    """Return True if name is a safe slug (no path chars, reasonable length)."""
    if not isinstance(name, str):
        return False
    if len(name) == 0 or len(name) > MAX_NAME_LENGTH:
        return False
    if ".." in name or "/" in name or "\\" in name:
        return False
    if not NAME_REGEX.match(name):
        return False
    return True


def _render_prompt_block(template: str) -> str:
    """Render a YAML block scalar for prompt_template."""
    if template is None:
        return "prompt_template: |\n  "
    lines = template.splitlines() or [""]
    return "prompt_template: |\n" + "\n".join("  " + line for line in lines) + "\n"


def _render_permissions_block(perms) -> str:
    """Render permissions as YAML sequence or empty list."""
    if not perms:
        return "permissions: []\n"
    if isinstance(perms, list):
        out = "permissions:\n"
        for p in perms:
            out += f"  - {p}\n"
        return out
    # Fallback: write single value
    return f"permissions: [{perms}]\n"


def _render_agent_yaml(spec: Dict) -> str:
    """Construct agent.yaml content from spec without external dependencies."""
    name = spec.get("name", "unknown_agent")
    description = spec.get("description", "")
    model = spec.get("model", "")
    provider = spec.get("provider", "")
    timeout = spec.get("timeout", 60)
    entrypoint = spec.get("entrypoint", "main.py")
    permissions = spec.get("permissions", [])
    prompt_template = spec.get("prompt_template", "")

    # YAML manual construction
    yaml = f"name: {name}\n"
    if "\n" in description:
        yaml += "description: |\n"
        for line in description.splitlines():
            yaml += f"  {line}\n"
    else:
        yaml += f"description: {description}\n"
    yaml += f"model: {model}\n"
    yaml += f"provider: {provider}\n"
    yaml += _render_prompt_block(prompt_template)
    yaml += _render_permissions_block(permissions)
    yaml += f"timeout: {timeout}\n"
    yaml += f"entrypoint: {entrypoint}\n"
    return yaml


def _render_main_py_skeleton(agent_name: str) -> str:
    """Return a Python main.py skeleton for the newly created agent."""
    return f'''from mcp_agent.agents.agent import Agent
from typing import Dict, Optional
import asyncio

# Per-agent runner fallback imports
try:
    from mcp_agent.llm_mcp_app.agent_runner import AgentRunner
    from mcp_agent.llm_mcp_app.providers import get_provider
    from mcp_agent.llm_mcp_app.models import Message
except ImportError:
    from llm_mcp_app.agent_runner import AgentRunner  # type: ignore
    from llm_mcp_app.providers import get_provider  # type: ignore
    from llm_mcp_app.models import Message  # type: ignore

def run(task: str, agent_config: Optional[Dict] = None) -> Dict[str, str]:
    """
    Run the agent. Uses AgentRunner when agent_config is provided, else falls back to a simple provider call.
    """
    if agent_config:
        runner = AgentRunner(agent_config)
        try:
            result = asyncio.run(runner.run(task))
            if isinstance(result, dict):
                return {'result': result.get('result', str(result))}
            return {'result': str(result)}
        except Exception:
            return {'result': "<error from AgentRunner>"}

    # Fallback behaviour: try to call provider.chat with Message objects.
    try:
        provider = get_provider("{agent_name}")
    except Exception:
        return {'result': "<no provider>"}

    messages = [Message(role="user", content=task)]
    try:
        generated = asyncio.run(provider.chat(messages))
        if isinstance(generated, dict):
            text = generated.get("result") or generated.get("generated_text") or str(generated)
        else:
            text = str(generated)
        return {'result': text}
    except Exception:
        return {'result': "<fallback message>"}

def generate(task: str, agent_config: Optional[Dict] = None) -> str:
    result = run(task, agent_config)
    if isinstance(result, dict):
        return result.get("result", str(result))
    return str(result)

def get_agent(agent_config: Optional[Dict] = None) -> Agent:
    """Return an Agent instance exposing generate(task) function."""
    def _generate(task: str) -> str:
        return generate(task, agent_config)

    instruction = "Agent {agent_name} generated by agent_creator."
    return Agent(name="{agent_name}", instruction=instruction, functions=[_generate])

if __name__ == "__main__":
    a = get_agent()
    print("Agent created:", a.name)
    print("Instruction:", a.instruction)
    print("\\nDemo generate call:")
    print(generate("Sample task"))
'''


def create_agent(spec: Dict, agent_config: Optional[Dict] = None) -> Dict:
    """
    Validate spec and create files for a new agent under mcp-agent/agents/{name}.
    Returns {"created": True, "path": "..."} on success or {"created": False, "error": "..."}.
    """
    if not isinstance(spec, dict):
        return {"created": False, "error": "spec must be a dict"}
    # Check required keys
    missing = [k for k in REQUIRED_KEYS if k not in spec]
    if missing:
        return {"created": False, "error": f"missing required keys: {', '.join(missing)}"}
    name = spec.get("name")
    if not _is_valid_name(name):
        return {"created": False, "error": "invalid name; must be alphanumeric with - or _, no path chars, max length 50"}
    entrypoint = spec.get("entrypoint")
    if entrypoint != "main.py":
        return {"created": False, "error": "entrypoint must be 'main.py'"}

    # Target directory
    base_dir = os.path.join("mcp-agent", "agents")
    target_dir = os.path.join(base_dir, name)
    if os.path.exists(target_dir):
        return {"created": False, "error": "target directory already exists"}

    try:
        os.makedirs(target_dir, exist_ok=False)
    except Exception as e:
        return {"created": False, "error": f"failed to create directory: {e}"}

    # Write agent.yaml
    yaml_text = _render_agent_yaml(spec)
    try:
        with open(os.path.join(target_dir, "agent.yaml"), "w", encoding="utf-8") as f:
            f.write(yaml_text)
    except Exception as e:
        return {"created": False, "error": f"failed to write agent.yaml: {e}"}

    # Write main.py skeleton
    main_py = _render_main_py_skeleton(name)
    try:
        with open(os.path.join(target_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write(main_py)
    except Exception as e:
        return {"created": False, "error": f"failed to write main.py: {e}"}

    return {"created": True, "path": os.path.join("mcp-agent", "agents", name)}


def run(task: str, agent_config: Optional[Dict] = None) -> Dict[str, str]:
    """
    Run-like wrapper to allow using AgentRunner for validations if needed.
    For agent_creator, 'task' is expected to be a JSON string or dict containing the spec.
    """
    spec = task
    if isinstance(task, str):
        try:
            spec = json.loads(task)
        except Exception:
            return {"result": "<invalid spec string>"}
    if agent_config:
        # Optionally validate spec via AgentRunner using agent_config
        try:
            runner = AgentRunner(agent_config)
            out = asyncio.run(runner.run(spec))
            if isinstance(out, dict):
                return {"result": out.get("result", str(out))}
            return {"result": str(out)}
        except Exception:
            # fall back to local create_agent behaviour
            pass
    # Call local create_agent and return result as string
    res = create_agent(spec)
    return {"result": json.dumps(res)}


def get_agent(agent_config: Optional[Dict] = None) -> Agent:
    """
    Exported agent that exposes a single function create_agent(spec) captured with agent_config.
    """
    def _create(spec):
        return create_agent(spec, agent_config)

    instruction = "Agent creator (agresář) that creates new agent directories and files from a spec dict."
    return Agent(name="agent_creator", instruction=instruction, functions=[_create])


if __name__ == "__main__":
    # Basic smoke test (does not write files unless create_agent is called)
    agent = get_agent()
    print("Agent created:", agent.name)
    demo_spec = {
        "name": "demo_agent",
        "description": "A demo agent created by agent_creator",
        "model": "gpt-4",
        "provider": "openai",
        "prompt_template": "{{prompt}}",
        "permissions": [],
        "timeout": 60,
        "entrypoint": "main.py",
    }
    print("Validation result:", create_agent(demo_spec))