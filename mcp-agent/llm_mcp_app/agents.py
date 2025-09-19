"""
Agent loading functionality for MCP Agent.
"""

import os
import importlib.util
from pathlib import Path
from typing import Dict

try:
    from mcp_agent.agents.agent import Agent
except ImportError as e:
    import logging
    logging.error(f"Failed to import Agent class. Make sure the script is run from the project root. Error: {e}")
    raise

try:
    from .config import logger, AGENTS_DIR
except ImportError:
    from config import logger, AGENTS_DIR


def load_all_agents(agents_dir: str = AGENTS_DIR) -> Dict[str, Agent]:
    """
    Dynamically loads all agents from the specified directory.
    Each agent is expected to be in a subdirectory and have a 'main.py'
    with a 'get_agent()' function that returns an Agent instance.
    """
    agents = {}
    base_path = Path(agents_dir)
    if not base_path.is_dir():
        logger.error(f"Agents directory not found: {agents_dir}")
        return agents

    for agent_name in os.listdir(base_path):
        agent_path = base_path / agent_name
        main_py_path = agent_path / "main.py"
        if agent_path.is_dir() and main_py_path.is_file():
            try:
                # Use a unique module name per load to allow hot-reload without module cache issues
                unique_mod_name = f"agents.{agent_name}.main_{os.urandom(4).hex()}"
                spec = importlib.util.spec_from_file_location(unique_mod_name, main_py_path)
                agent_module = importlib.util.module_from_spec(spec)
                # Ensure loader exists before exec
                if spec.loader is None:
                    logger.error(f"No loader for module spec of agent {agent_name}")
                    continue
                spec.loader.exec_module(agent_module)

                if hasattr(agent_module, "get_agent"):
                    agent_instance = agent_module.get_agent()
                    agents[agent_name] = agent_instance
                    logger.info(f"Successfully loaded agent: {agent_name}")
                else:
                    logger.warning(f"'get_agent' function not found in {main_py_path}")
            except Exception as e:
                logger.error(f"Error loading agent '{agent_name}': {e}")
    
    return agents
