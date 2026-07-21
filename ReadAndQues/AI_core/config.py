"""
ReadAndQues/AI_core/config.py — LLM & Exam configuration for ReadAndQues.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, SecretStr

logger = logging.getLogger(__name__)

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


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


def get_llm(temperature: float = 0.3):
    """
    Return a configured LLM instance.

    Checks Azure OpenAI settings first, then Google Gemini / OpenAI settings.
    """
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if azure_key:
        from langchain_openai import ChatOpenAI
        endpoint = os.getenv(
            "AZURE_OPENAI_ENDPOINT",
            "https://myfirstazureproject-614-resource.services.ai.azure.com/openai/v1",
        )
        model = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-5-mini")
        return ChatOpenAI(
            base_url=endpoint,
            api_key=SecretStr(azure_key),
            model=model,
            temperature=temperature,
        )
    elif gemini_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=gemini_key,
            temperature=temperature,
            max_retries=2,
        )
    elif openai_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            api_key=SecretStr(openai_key),
            model="gpt-4o-mini",
            temperature=temperature,
        )
    else:
        raise ValueError("No LLM API keys found (AZURE_OPENAI_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY).")
