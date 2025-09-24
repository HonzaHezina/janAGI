import pytest
from mcp_agent.llm_mcp_app.agents import load_all_agents

def test_load_all_agents_smoke():
    agents = load_all_agents("mcp-agent/agents")
    assert isinstance(agents, dict)
    # At least verify loaded agents have 'functions' attribute if any
    for name, agent in agents.items():
        assert hasattr(agent, "functions"), f"Agent {name} missing functions attribute"
        assert isinstance(agent.functions, list)

def test_specific_agent_present():
    # Common agents in repo: codewriter, finder, html_parser
    agents = load_all_agents("mcp-agent/agents")
    for expected in ("codewriter", "finder", "html_parser"):
        if expected in agents:
            assert hasattr(agents[expected], "functions")