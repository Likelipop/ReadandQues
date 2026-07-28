import logging
from typing import Callable, Dict

logger = logging.getLogger(__name__)

# Registry for jobs and pipelines
_JOBS: Dict[str, Callable] = {}
_PIPES: Dict[str, "Pipe"] = {}


def job(name: str):
    """
    Decorator to register a function as a job.
    """

    def decorator(func: Callable):
        _JOBS[name] = func
        logger.info(f"Registered job: {name}")
        return func

    return decorator


def get_job(name: str) -> Callable:
    if name not in _JOBS:
        raise ValueError(f"Job '{name}' not found.")
    return _JOBS[name]


def register_pipe(name: str, pipe: "Pipe"):
    _PIPES[name] = pipe
    logger.info(f"Registered pipe: {name}")


def get_pipe(name: str) -> "Pipe":
    if name not in _PIPES:
        raise ValueError(f"Pipe '{name}' not found.")
    return _PIPES[name]
