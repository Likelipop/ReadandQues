import logging
from typing import Any

from service.ai_core.platform import AITool, AIToolPolicy, AIToolRunResult, register_ai_tool

logger = logging.getLogger(__name__)


class ExplainedTool(AITool):
    name = "explained"
    version = "1.0.0"
    model_profile = "default"

    def run(self, input_data: dict[str, Any], user_id: int | None = None) -> AIToolRunResult:
        def _execute():
            from service.ai_core.graphs import run_explained_flow

            return run_explained_flow(
                phrase=input_data.get("phrase", ""),
                paragraph_context=input_data.get("paragraph_context", ""),
            )

        return AIToolPolicy.execute(
            tool_name=self.name,
            version=self.version,
            func=_execute,
            input_data=input_data,
            user_id=user_id,
            use_cache=False,
        )


explained_tool = ExplainedTool()
register_ai_tool(explained_tool)
