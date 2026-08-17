from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class AIToolRunResult(BaseModel):
    """Structured result container for an AI tool invocation."""

    run_id: str
    tool_name: str
    version: str
    model_name: str = "azure_gpt"
    status: str  # "completed" | "failed"
    output: Any = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_ms: float = 0.0
    error: str | None = None


class AITool(ABC):
    """Abstract base class for all versioned AI tools."""

    name: str
    version: str
    model_profile: str = "default"

    @abstractmethod
    def run(self, input_data: dict[str, Any], user_id: int | None = None) -> AIToolRunResult:
        """Executes the AI tool logic and returns a structured AIToolRunResult."""
        pass
