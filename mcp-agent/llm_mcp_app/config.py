"""
Configuration module for MCP Agent.
Handles environment variables, logging setup, and system paths.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# --- System Path Setup ---
sys.path.insert(0, r'C:\Users\janhe\projekty\janAGI\mcp-agent\src')

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Environment Variables Loading ---
if not load_dotenv():
    logger.warning("No .env file found. Relying on system environment variables.")

# --- Configuration Constants ---
AGENTS_DIR = "agents"

# --- LLM Provider Configuration ---
# Hlavní LLM provider pro orchestraci (lze změnit)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # Default to Gemini
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt2")

# API konfigurace
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
HUGGINGFACE_API_BASE = "https://api-inference.huggingface.co/models"
OPENAI_API_BASE = "https://api.openai.com/v1"

# API klíče
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")  # Support both names
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Výchozí modely pro různé providery
DEFAULT_MODELS = {
    "gemini": "gemini-1.5-flash",
    "huggingface": "gpt2",  # Basic, fast and always available
    "openai": "gpt-3.5-turbo"
}
