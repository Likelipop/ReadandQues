import logging

from pipeline.etl.registry import get_job, register_pipe

logger = logging.getLogger(__name__)


class Pipe:
    def __init__(self, name: str):
        self.name = name
        self.jobs = []
        register_pipe(name, self)

    def add_job(self, job_name: str) -> "Pipe":
        self.jobs.append(job_name)
        return self

    def invoke(self, **kwargs) -> dict:
        logger.info(f"🚀 Starting pipeline: {self.name}")
        results = {}
        for job_name in self.jobs:
            logger.info(f"▶️ Executing job: {job_name}")
            try:
                job_func = get_job(job_name)
                job_res = job_func(**kwargs)
                results[job_name] = job_res
                logger.info(f"✅ Job '{job_name}' completed. Result: {job_res}")
            except Exception as e:
                logger.error(f"❌ Job '{job_name}' failed: {e}")
                results[job_name] = {"status": "failed", "error": str(e)}
                logger.error(f"🛑 Pipeline '{self.name}' aborted due to job failure.")
                return {"status": "failed", "results": results}

        logger.info(f"🎉 Pipeline '{self.name}' finished successfully.")
        return {"status": "completed", "results": results}
