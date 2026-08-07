import hashlib
import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, Optional

from service.ai_core.platform.contracts import AIToolRunResult

logger = logging.getLogger(__name__)

_AI_CACHE: Dict[str, Any] = {}


def clear_ai_cache() -> None:
    _AI_CACHE.clear()


def hash_input(input_data: Dict[str, Any]) -> str:
    serialized = json.dumps(input_data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def log_ai_run(
    run_result: AIToolRunResult,
    input_payload: Dict[str, Any],
    user_id: Optional[int] = None
) -> None:
    """Persists an AIRunLog entry to PostgreSQL."""
    try:
        from django.conf import settings
        if not settings.configured:
            return
        from service.models import AIRunLog
        AIRunLog.objects.create(
            run_id=run_result.run_id,
            user_id=user_id,
            tool_name=run_result.tool_name,
            tool_version=run_result.version,
            model_name=run_result.model_name,
            status=run_result.status,
            prompt_tokens=run_result.prompt_tokens,
            completion_tokens=run_result.completion_tokens,
            total_tokens=run_result.total_tokens,
            duration_ms=run_result.duration_ms,
            input_payload=input_payload,
            output_payload=run_result.output if isinstance(run_result.output, dict) else {"result": str(run_result.output)},
            error_message=run_result.error or "",
        )
        logger.info(f"Persisted AIRunLog run_id={run_result.run_id}")
    except Exception as e:
        logger.warning(f"Could not persist AIRunLog record (DB might be offline): {e}")


class AIToolPolicy:
    """Policy wrapper enforcing timing, caching, token usage, and persistence for AI tools."""

    @staticmethod
    def execute(
        tool_name: str,
        version: str,
        func: Callable[[], Any],
        input_data: Dict[str, Any],
        user_id: Optional[int] = None,
        model_name: str = "azure_gpt",
        use_cache: bool = False,
    ) -> AIToolRunResult:
        run_id = f"run_{uuid.uuid4().hex[:16]}"
        cache_key = f"{tool_name}:{version}:{hash_input(input_data)}"

        if use_cache and cache_key in _AI_CACHE:
            logger.info(f"AI Cache Hit for '{tool_name}' ({cache_key[:12]})")
            cached_output = _AI_CACHE[cache_key]
            res = AIToolRunResult(
                run_id=run_id,
                tool_name=tool_name,
                version=version,
                model_name=model_name,
                status="completed",
                output=cached_output,
                duration_ms=0.0,
            )
            log_ai_run(res, input_data, user_id)
            return res

        start_time = time.perf_counter()
        try:
            output = func()
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            if use_cache and output:
                _AI_CACHE[cache_key] = output

            res = AIToolRunResult(
                run_id=run_id,
                tool_name=tool_name,
                version=version,
                model_name=model_name,
                status="completed",
                output=output,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"AI Tool '{tool_name}' failed: {e}")
            res = AIToolRunResult(
                run_id=run_id,
                tool_name=tool_name,
                version=version,
                model_name=model_name,
                status="failed",
                error=str(e),
                duration_ms=duration_ms,
            )

        log_ai_run(res, input_data, user_id)
        return res
