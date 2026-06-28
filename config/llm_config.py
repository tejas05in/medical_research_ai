import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------
# Which LLM backend to use for structured evidence extraction.
# Set LLM_PROVIDER=openai in .env to switch to OpenAI.
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()

# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "openai/gpt-4.1")

# ---------------------------------------------------------------------------
# CrewAI agent LLMs  (provider/model format expected by CrewAI)
# ---------------------------------------------------------------------------
# Used by frontend/crew_runner.py when building agents programmatically.
AGENT_SEARCH_LLM: str = os.getenv("AGENT_SEARCH_LLM", "openai/gpt-4.1")
AGENT_EVIDENCE_LLM: str = os.getenv("AGENT_EVIDENCE_LLM", "openai/gpt-4.1-mini")
