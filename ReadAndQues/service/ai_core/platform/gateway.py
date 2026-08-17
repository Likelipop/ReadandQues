import logging
from typing import Any

from pydantic import BaseModel, Field

from service.ai_core.connection.router import default_router

logger = logging.getLogger(__name__)


class ModelProfile(BaseModel):
    name: str
    temperature: float = 0.3
    fallback_order: list[str] = Field(default_factory=lambda: ["azure"])


class ModelGateway:
    """Gateway for managing LLM model profiles and standardizing model access."""

    PROFILES: dict[str, ModelProfile] = {
        "default": ModelProfile(name="default", temperature=0.3),
        "creative": ModelProfile(name="creative", temperature=0.7),
        "precise": ModelProfile(name="precise", temperature=0.1),
    }

    @classmethod
    def get_llm(cls, profile_name: str = "default", temperature: float | None = None) -> Any:
        profile = cls.PROFILES.get(profile_name, cls.PROFILES["default"])
        temp = temperature if temperature is not None else profile.temperature
        return default_router.get_llm(temperature=temp)
