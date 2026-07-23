"""
worker_service/ai_core/config.py — LLM configuration (standalone, no Django).

Loads .env from the project root directory.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, SecretStr

# Load .env from project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT",
    "https://myfirstazureproject-614-resource.services.ai.azure.com/openai/v1",
)
_MODEL = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-5-mini")

if not _API_KEY:
    raise ValueError("Missing AZURE_OPENAI_API_KEY in .env or environment variables.")


class ExamConfig(BaseModel):
    word_count: int
    total_questions: int

    @classmethod
    def from_text(cls, text: str) -> "ExamConfig":
        wc = len(text.strip().split())
        if wc < 500:
            total = 7
        elif wc <= 800:
            total = 10
        else:
            total = 14
        return cls(word_count=wc, total_questions=total)


def get_llm(temperature: float = 0.3) -> AzureChatOpenAI:
    """
    Return a configured LLM instance.

    temperature=0.0  → deterministic; use for analyzer (genre grounding) and verifier.
    temperature=0.3  → default; use for question_planner (needs creative variation).
    """
    # Fix the endpoint for Azure if it ends in /openai/v1
    base_endpoint = _ENDPOINT
    if base_endpoint.endswith("/openai/v1"):
        base_endpoint = base_endpoint.replace("/openai/v1", "")

    # The model (like o1/o3-mini) might only support temperature=1
    return AzureChatOpenAI(
        azure_endpoint=base_endpoint,
        api_key=SecretStr(_API_KEY),
        azure_deployment=_MODEL,
        api_version="2023-05-15",
        max_retries=10,
        timeout=180.0,
        # temperature=temperature  # omitted because o-series rejects temp != 1
    )
