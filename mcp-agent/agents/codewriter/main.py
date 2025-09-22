from mcp_agent.agents.agent import Agent
from typing import Dict, Optional
import asyncio
import os

# Try to use PyYAML to load local agent.yaml when running standalone
try:
    import yaml
except Exception:
    yaml = None

# Prefer per-agent runner and allow agent-specific model/provider via agent_config.
# We keep previous fallback using get_provider for backward compatibility.
try:
    from mcp_agent.llm_mcp_app.agent_runner import AgentRunner
    from mcp_agent.llm_mcp_app.providers import get_provider
    from mcp_agent.llm_mcp_app.models import Message
except ImportError:
    # Support running from project root or examples
    from llm_mcp_app.agent_runner import AgentRunner
    from llm_mcp_app.providers import get_provider
    from llm_mcp_app.models import Message


def run(task: str, agent_config: Optional[Dict] = None) -> Dict[str, str]:
    """
    Run the CodeWriter agent. If agent_config is provided, use AgentRunner which
    composes prompt_template and invokes the configured provider.

    If agent_config is not provided (standalone invocation), try to load the
    local agent.yaml to obtain model/provider/prompt_template and use AgentRunner.
    Falls back to the legacy behaviour using a hard-coded 'codestral' model via get_provider().
    """
    # If caller supplied agent_config, use it (normal server loader path)
    if agent_config:
        runner = AgentRunner(agent_config)
        try:
            result = asyncio.run(runner.run(task))
            # runner.run returns a dict {"result": ...}
            if isinstance(result, dict):
                return {"result": result.get("result", str(result))}
            return {"result": str(result)}
        except Exception:
            return {"result": "<fallback message>"}

    # Try to load local agent.yaml when running the agent standalone (developer convenience)
    try:
        if yaml:
            here = os.path.dirname(__file__)
            yaml_path = os.path.join(here, "agent.yaml")
            if os.path.isfile(yaml_path):
                with open(yaml_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    agent_config = loaded
    except Exception:
        # Ignore loading errors and continue to legacy fallback
        agent_config = agent_config or None

    # If we now have agent_config (from file), use AgentRunner
    if agent_config:
        runner = AgentRunner(agent_config)
        try:
            result = asyncio.run(runner.run(task))
            if isinstance(result, dict):
                return {"result": result.get("result", str(result))}
            return {"result": str(result)}
        except Exception:
            return {"result": "<fallback message>"}

    # Legacy fallback: call provider directly with model "codestral"
    model_name = "codestral"
    try:
        provider = get_provider(model_name)
    except Exception:
        return {"result": "<fallback message>"}

    messages = [Message(role="user", content=task)]
    try:
        generated = asyncio.run(provider.chat(messages))
        if isinstance(generated, dict):
            text = generated.get("result") or generated.get("generated_text") or str(generated)
        else:
            text = str(generated)
        return {"result": text}
    except Exception:
        return {"result": "<fallback message>"}


def generate_code(task: str, agent_config: Optional[Dict] = None) -> str:
    """
    Generates code based on the given task description.
    Uses AgentRunner when agent_config is provided.
    """
    result = run(task, agent_config)
    if isinstance(result, dict):
        return result.get("result", str(result))
    return str(result)


def get_agent(agent_config: Optional[Dict] = None) -> Agent:
    """
    Creates and returns the codewriter agent.
    Accepts optional agent_config passed by the loader; this allows per-agent LLM + prompt configuration.
    """
    # Capture agent_config in the closure so the exported function uses it
    def _generate_code(task: str) -> str:
        return generate_code(task, agent_config)

    instruction = (
        "You are a helpful agent that can generate code based on task descriptions. "
        "By default this agent uses Mistral 'codestral', but agent_config can override model/provider/prompt."
    )

    return Agent(
        name="codewriter",
        instruction=instruction,
        functions=[_generate_code],
    )


if __name__ == "__main__":
    # Local smoke test (note: may require PYTHONPATH to include mcp-agent/src and mcp-agent)
    codewriter_agent = get_agent()
    print(f"Agent '{codewriter_agent.name}' created.")
    print(f"Instruction: {codewriter_agent.instruction}")
    print("\nTesting the generate_code function...")
    result = generate_code("Create a Python function that calculates fibonacci numbers")
    print(result)
