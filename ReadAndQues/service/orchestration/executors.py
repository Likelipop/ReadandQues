import logging
import threading
from typing import Any, Callable, Dict

from service.orchestration.contracts import PipelineResult

logger = logging.getLogger(__name__)


class InlineExecutor:
    """Synchronous pipeline executor."""

    @staticmethod
    def execute(pipeline: Any, **kwargs) -> PipelineResult:
        return pipeline.invoke(**kwargs)


class ThreadedBackgroundExecutor:
    """Asynchronous background thread pipeline executor."""

    @staticmethod
    def submit(pipeline: Any, callback: Callable[[PipelineResult], None] = None, **kwargs) -> threading.Thread:
        def worker():
            try:
                res = pipeline.invoke(**kwargs)
                if callback:
                    callback(res)
            except Exception as e:
                logger.error(f"Async pipeline execution failed for '{pipeline.name}': {e}")

        thread = threading.Thread(
            target=worker,
            name=f"PipelineWorker-{pipeline.name}",
            daemon=True
        )
        thread.start()
        return thread
