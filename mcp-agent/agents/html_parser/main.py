from mcp_agent.agents.agent import Agent
from typing import Dict, Optional
import asyncio

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
    Run the HTML parser agent. If agent_config is provided, use AgentRunner.
    Otherwise fall back to the legacy behaviour using a hard-coded model via get_provider().
    """
    if agent_config:
        runner = AgentRunner(agent_config)
        try:
            result = asyncio.run(runner.run(task))
            if isinstance(result, dict):
                return {"result": result.get("result", str(result))}
            return {"result": str(result)}
        except Exception:
            return {"result": "<fallback message>"}

    # Legacy fallback: call provider directly with model "gpt-4"
    model_name = "gpt-4"
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


def generate_parse_html(url: str, agent_config: Optional[Dict] = None) -> str:
    """
    Generates parsed HTML text for the given URL using the configured agent or fallback provider.
    """
    # For LLM-based parsing we pass a simple instruction + url as the task
    task = f"Fetch and parse HTML from: {url}"
    result = run(task, agent_config)
    if isinstance(result, dict):
        return result.get("result", str(result))
    return str(result)


def get_agent(agent_config: Optional[Dict] = None) -> Agent:
    """
    Creates and returns the html_parser agent.
    Accepts optional agent_config passed by the loader; this allows per-agent LLM + prompt configuration.
    """
    def _parse_html(task: str) -> str:
        return generate_parse_html(task, agent_config)

    instruction = (
        "You are a helpful agent that can fetch and parse HTML from web pages. "
        "By default this agent uses gpt-4, but agent_config can override model/provider/prompt."
    )

    return Agent(
        name="html_parser",
        instruction=instruction,
        functions=[_parse_html],
        # server_names=["fetch"],
    )


if __name__ == "__main__":
    parser_agent = get_agent()
    print(f"Agent '{parser_agent.name}' created.")
    print(f"Instruction: {parser_agent.instruction}")

    # To test the function directly:
    print("\nTesting the generate_parse_html function...")
    result = generate_parse_html("https://example.com")
    print(result)

