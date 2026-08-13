from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PipelineContext(BaseModel):
    """Strongly-typed container for pipeline execution context."""

    data: Dict[str, Any] = Field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def update(self, items: Dict[str, Any]) -> None:
        self.data.update(items)

    def contains(self, key: str) -> bool:
        return key in self.data

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.data)


class JobResult(BaseModel):
    """Structured result of executing a single job."""

    job_name: str
    status: str  # "completed" | "failed"
    output: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class PipelineResult(BaseModel):
    """Structured result of executing an entire pipeline."""

    pipeline_name: str
    status: str  # "completed" | "failed"
    results: Dict[str, JobResult] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
