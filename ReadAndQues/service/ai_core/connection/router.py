import logging
from typing import Any

# Ensure providers are loaded and registered
import service.ai_core.connection.providers  # noqa: F401
from service.ai_core.connection.registry import get_all_providers

logger = logging.getLogger(__name__)


class ModelRouter:
    def __init__(self, fallback_order: list[str] = None):
        self.fallback_order = fallback_order or ["azure"]

    def get_llm(self, temperature: float = 0.3) -> Any:
        providers = get_all_providers()
        available_llms = []

        for provider_name in self.fallback_order:
            if provider_name in providers:
                try:
                    factory = providers[provider_name]
                    llm = factory(temperature)
                    available_llms.append(llm)
                except Exception as e:
                    logger.error(f"Failed to initialize provider '{provider_name}': {e}")
            else:
                logger.warning(f"Provider '{provider_name}' is not registered.")

        if not available_llms:
            raise RuntimeError("No LLM providers could be initialized.")

        primary_llm = available_llms[0]

        if len(available_llms) > 1:
            # Langchain's with_fallbacks adds fault tolerance automatically during API calls
            return primary_llm.with_fallbacks(available_llms[1:])

        return primary_llm


default_router = ModelRouter(fallback_order=["azure"])


def get_llm(temperature: float = 0.3) -> Any:
    """
    Returns an LLM configured with fallbacks for fault tolerance.
    """
    return default_router.get_llm(temperature=temperature)
