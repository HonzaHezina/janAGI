from typing import Dict, Any, Optional
from .providers import get_provider
from .models import Message

class AgentRunner:
    """
    AgentRunner composes a prompt from an agent's prompt_template and runtime task,
    instantiates the appropriate provider, and executes the call. Returns a normalized result.
    """

    def __init__(self, agent_config: Dict[str, Any]):
        self.agent_config = agent_config
        self.model = agent_config.get("model")
        self.provider_override = agent_config.get("provider")
        self.prompt_template = agent_config.get("prompt_template", "{{task}}")
        self.timeout = agent_config.get("timeout", 30)

    def _build_prompt(self, task: str) -> str:
        # Simple templating using replace; keep minimal to avoid heavy deps.
        return self.prompt_template.replace("{{task}}", task)

    async def run(self, task: str) -> Dict[str, Any]:
        model = self.model or self.agent_config.get("default_model")
        provider = get_provider(model, self.provider_override) if model else get_provider(self.provider_override or "dummy")
        # Build messages in project Message format
        messages = [Message(role="user", content=self._build_prompt(task))]
        try:
            content = await provider.chat(messages, max_tokens=None, temperature=0.7)
            return {"result": content, "model": model, "provider": provider.__class__.__name__}
        except Exception as e:
            return {"result": f"[ERROR] {e}", "model": model, "provider": provider.__class__.__name__}
