"""
ai_service/connection.py — Direct Azure OpenAI LLM Connection Factory.

Provides a clean factory interface to initialize Azure OpenAI models.
"""

import logging
import os

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr

logger = logging.getLogger(__name__)

# Load environment variables once at module import
load_dotenv()


def get_azure_llm(temperature: float = 1.0) -> AzureChatOpenAI:
    """
    Initialize and return an AzureChatOpenAI client using environment configuration.
    """
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Missing AZURE_OPENAI_API_KEY in environment variables.")

    endpoint = os.getenv(
        "AZURE_OPENAI_ENDPOINT",
        "https://myfirstazureproject-614-resource.services.ai.azure.com",
    )
    if endpoint.endswith("/openai/v1"):
        endpoint = endpoint.replace("/openai/v1", "")

    deployment = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-5-mini")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

    return AzureChatOpenAI(
        azure_endpoint=endpoint,
        api_key=SecretStr(api_key),
        azure_deployment=deployment,
        api_version=api_version,
        temperature=temperature,
        streaming=True,
        max_retries=3,
        timeout=60.0,
    )


def get_llm(temperature: float = 1.0) -> AzureChatOpenAI:
    """
    Standard helper to retrieve the primary LLM instance.
    Defaults to 1.0 for gpt-5-mini compatibility.
    """
    return get_azure_llm(temperature=temperature)


class ModelRouter:
    """
    Model routing factory wrapper providing access to configured LLM instances.
    """

    @staticmethod
    def get_llm(temperature: float = 1.0) -> AzureChatOpenAI:
        """Retrieve the configured LLM instance."""
        return get_azure_llm(temperature=temperature)


