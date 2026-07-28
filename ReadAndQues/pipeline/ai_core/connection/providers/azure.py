import os

from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr

from pipeline.ai_core.connection.registry import register_provider

_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT",
    "https://myfirstazureproject-614-resource.services.ai.azure.com/openai/v1",
)
_MODEL = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-5-mini")


@register_provider("azure")
def get_azure_llm(temperature: float = 0.3) -> AzureChatOpenAI:
    if not _API_KEY:
        raise ValueError("Missing AZURE_OPENAI_API_KEY in .env or environment variables.")

    base_endpoint = _ENDPOINT
    if base_endpoint.endswith("/openai/v1"):
        base_endpoint = base_endpoint.replace("/openai/v1", "")

    return AzureChatOpenAI(
        azure_endpoint=base_endpoint,
        api_key=SecretStr(_API_KEY),
        azure_deployment=_MODEL,
        api_version="2023-05-15",
        max_retries=10,
        timeout=180.0,
        temperature=temperature,
    )
