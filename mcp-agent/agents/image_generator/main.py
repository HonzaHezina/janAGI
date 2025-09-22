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
    Run the Image Generator agent. If agent_config is provided, use AgentRunner which
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

    # Legacy fallback: call provider directly with model "flex" and prefer huggingface provider
    model_name = "flex"
    try:
        # provider factory may accept a provider override; pass "huggingface" to prefer HF
        provider = get_provider(model_name, provider_override="huggingface")
    except TypeError:
        # Some older versions accept only one argument
        try:
            provider = get_provider(model_name)
        except Exception:
            return {"result": "<fallback message>"}
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


def generate_image_from_prompt(prompt: str = "a cat in a hat", agent_config: Optional[Dict] = None) -> str:
    """
    Generates an image (or an image description/url) by delegating to run().
    The agent follows the pattern used in codewriter: use AgentRunner when agent_config is provided,
    otherwise fall back to get_provider() with model 'flex' and provider 'huggingface'.
    """
    result = run(prompt, agent_config)
    if isinstance(result, dict):
        return result.get("result", str(result))
    return str(result)


def get_agent(agent_config: Optional[Dict] = None) -> Agent:
    """
    Creates and returns the image_generator agent.
    Accepts optional agent_config passed by the loader; this allows per-agent LLM + prompt configuration.
    """
    def _generate_image(task: str) -> str:
        return generate_image_from_prompt(task, agent_config)

    instruction = (
        "You are an agent that generates images from text prompts. "
        "By default this agent uses model 'flex' with provider 'huggingface', but agent_config can override model/provider/prompt."
    )

    return Agent(
        name="image_generator",
        instruction=instruction,
        functions=[_generate_image],
    )


if __name__ == "__main__":
    # Example of how to get and use the agent
    image_agent = get_agent()
    print(f"Agent '{image_agent.name}' created.")
    print(f"Instruction: {image_agent.instruction}")
    
    # To test the function directly:
    print("\nTesting the generate_image_from_prompt function...")
    result = generate_image_from_prompt("a futuristic city skyline at sunset")
    print(result)