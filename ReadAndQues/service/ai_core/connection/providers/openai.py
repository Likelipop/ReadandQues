import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from service.ai_core.connection.registry import register_provider


@register_provider("openai")
def get_openai_llm(temperature: float = 0.3) -> ChatOpenAI:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY in environment variables.")

    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL", None)

    return ChatOpenAI(
        model=model_name,
        api_key=SecretStr(api_key),
        base_url=base_url,
        temperature=temperature,
        max_retries=3,
        timeout=60.0,
    )
