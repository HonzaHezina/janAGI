"""
Configuration module for MCP Agent.
Handles environment variables, logging setup, and system paths.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# --- System Path Setup ---
# Přidáme root projektu (obsahuje balíček llm_mcp_app) i adresář src (obsahuje mcp_agent)
from pathlib import Path
PKG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PKG_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Debug informace pro ověření správného sys.path (jen na debug úrovni)
try:
    logger.debug(f"[llm_mcp_app.config] sys.path[:5]={sys.path[:5]} PROJECT_ROOT={PROJECT_ROOT}")
except Exception:
    pass

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

# Mistral / Codestral configuration
MISTRAL_API_BASE = os.getenv("MISTRAL_API_BASE", "https://api.mistral.ai")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
# API klíče
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")  # Support both names
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Výchozí modely pro různé providery
# Aktualizace: gemini default změněn na -latest kvůli 404 na původním názvu.
DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "huggingface": "gpt2",  # Basic, fast and always available
    "openai": "gpt-3.5-turbo"
}
