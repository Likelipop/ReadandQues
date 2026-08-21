import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from service.ai_core.connection.registry import register_provider


@register_provider("ollama")
def get_ollama_llm(temperature: float = 0.3) -> ChatOpenAI:
    load_dotenv()
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    model_name = os.getenv("OLLAMA_MODEL", "llama3.2")

    return ChatOpenAI(
        model=model_name,
        api_key=SecretStr("ollama"),
        base_url=base_url,
        temperature=temperature,
        max_retries=2,
        timeout=60.0,
    )
