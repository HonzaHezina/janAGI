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
    Run the Finder agent. If agent_config is provided, use AgentRunner which
    composes prompt_template and invokes the configured provider. Otherwise fall
    back to the legacy behaviour using a hard-coded model via get_provider().
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


def generate_find_files(query: str, agent_config: Optional[Dict] = None) -> str:
    """
    Generates finder results based on the given query.
    """
    result = run(query, agent_config)
    if isinstance(result, dict):
        return result.get("result", str(result))
    return str(result)


def get_agent(agent_config: Optional[Dict] = None) -> Agent:
    """
    Creates and returns the finder agent.
    Accepts optional agent_config passed by the loader; this allows per-agent LLM + prompt configuration.
    """
    def _find_files(task: str) -> str:
        return generate_find_files(task, agent_config)

    instruction = (
        "You are a helpful agent that can find files on the filesystem. "
        "By default this agent uses gpt-4, but agent_config can override model/provider/prompt."
    )

    return Agent(
        name="finder",
        instruction=instruction,
        functions=[_find_files],
        # server_names=["filesystem"],
    )


if __name__ == "__main__":
    finder_agent = get_agent()
    print(f"Agent '{finder_agent.name}' created.")
    print(f"Instruction: {finder_agent.instruction}")

    print("\nTesting the generate_find_files function...")
    result = generate_find_files("report.docx")
    print(result)
