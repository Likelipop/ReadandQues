import logging
import time
from typing import Any, Dict

from service.orchestration.configuration.registry import get_job, register_pipe
from service.orchestration.contracts import JobResult, PipelineContext, PipelineResult
from service.orchestration.exceptions import MissingContextError, PipelineValidationError

logger = logging.getLogger(__name__)


class Pipe:
    def __init__(self, name: str):
        self.name = name
        self.jobs = []
        register_pipe(name, self)

    def add_job(self, job_name: str) -> "Pipe":
        self.jobs.append(job_name)
        return self

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        """Validates that all jobs in the pipeline have required inputs available."""
        available_keys = set(context.keys())
        for job_name in self.jobs:
            job_func = get_job(job_name)
            job_inputs = getattr(job_func, "job_inputs", [])
            job_outputs = getattr(job_func, "job_outputs", [])

            missing = [k for k in job_inputs if k not in available_keys]
            if missing:
                logger.warning(f"Validation warning: Job '{job_name}' in pipeline '{self.name}' expects missing inputs: {missing}")

            # Simulate output keys becoming available for downstream jobs
            available_keys.update(job_outputs)

    def invoke(self, **kwargs) -> dict:
        logger.info(f"🚀 Starting pipeline: {self.name}")
        context = kwargs.copy()
        results = {}

        self.validate_inputs(context)

        for job_name in self.jobs:
            logger.info(f"▶️ Executing job: {job_name}")
            start_time = time.perf_counter()
            try:
                job_func = get_job(job_name)
                job_inputs = getattr(job_func, "job_inputs", [])
                job_outputs = getattr(job_func, "job_outputs", [])

                # Prepare inputs
                if job_inputs:
                    job_kwargs = {k: context[k] for k in job_inputs if k in context}
                else:
                    # Backward compatibility
                    job_kwargs = context.copy()

                job_res = job_func(**job_kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                results[job_name] = job_res

                # Process outputs into context
                if job_outputs:
                    if isinstance(job_res, dict):
                        for out_key in job_outputs:
                            if out_key in job_res:
                                context[out_key] = job_res[out_key]
                    else:
                        if len(job_outputs) == 1:
                            context[job_outputs[0]] = job_res
                        elif isinstance(job_res, (list, tuple)) and len(job_outputs) == len(job_res):
                            for i, out_key in enumerate(job_outputs):
                                context[out_key] = job_res[i]
                elif isinstance(job_res, dict):
                    # Merge dictionary output into context for backward compatibility
                    context.update(job_res)

                logger.info(f"✅ Job '{job_name}' completed in {duration_ms:.2f}ms.")
            except Exception as e:
                logger.error(f"❌ Job '{job_name}' failed: {e}")
                results[job_name] = {"status": "failed", "error": str(e)}
                logger.error(f"🛑 Pipeline '{self.name}' aborted due to job failure.")
                return {"status": "failed", "results": results, "context": context}

        logger.info(f"🎉 Pipeline '{self.name}' finished successfully.")
        return {"status": "completed", "results": results, "context": context}
