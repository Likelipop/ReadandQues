class OrchestrationError(Exception):
    """Base exception for all orchestration errors."""
    pass


class JobFailedError(OrchestrationError):
    """Raised when a single job fails during pipeline execution."""
    def __init__(self, job_name: str, message: str):
        self.job_name = job_name
        self.message = message
        super().__init__(f"Job '{job_name}' failed: {message}")


class MissingContextError(OrchestrationError):
    """Raised when a job is missing required input context keys."""
    def __init__(self, job_name: str, missing_keys: list[str]):
        self.job_name = job_name
        self.missing_keys = missing_keys
        super().__init__(f"Job '{job_name}' missing required context keys: {missing_keys}")


class PipelineValidationError(OrchestrationError):
    """Raised when a pipeline fails pre-execution validation."""
    def __init__(self, pipeline_name: str, message: str):
        self.pipeline_name = pipeline_name
        self.message = message
        super().__init__(f"Pipeline '{pipeline_name}' validation error: {message}")
