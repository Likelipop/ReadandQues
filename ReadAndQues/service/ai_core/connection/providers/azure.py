import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr

from service.ai_core.connection.registry import register_provider


@register_provider("azure")
def get_azure_llm(temperature: float = 1.0) -> AzureChatOpenAI:
    load_dotenv()
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Missing AZURE_OPENAI_API_KEY in .env or environment variables.")

    endpoint = os.getenv(
        "AZURE_OPENAI_ENDPOINT",
        "https://myfirstazureproject-614-resource.services.ai.azure.com",
    )
    if endpoint.endswith("/openai/v1"):
        endpoint = endpoint.replace("/openai/v1", "")

    deployment = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-5-mini")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

    # Reasoning and next-gen Azure models (gpt-5-mini, o1, o3) only support temperature=1.0
    effective_temp = temperature
    if any(m in deployment.lower() for m in ["gpt-5", "o1", "o3", "o-"]):
        effective_temp = 1.0

    return AzureChatOpenAI(
        azure_endpoint=endpoint,
        api_key=SecretStr(api_key),
        azure_deployment=deployment,
        api_version=api_version,
        max_retries=3,
        timeout=60.0,
        temperature=effective_temp,
    )
