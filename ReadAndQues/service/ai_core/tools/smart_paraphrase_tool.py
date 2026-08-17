import logging
from typing import Any

from service.ai_core.platform import AITool, AIToolPolicy, AIToolRunResult, register_ai_tool

logger = logging.getLogger(__name__)


class SmartParaphraseTool(AITool):
    name = "smart_paraphrase"
    version = "1.0.0"
    model_profile = "default"

    def run(self, input_data: dict[str, Any], user_id: int | None = None) -> AIToolRunResult:
        def _execute():
            from service.ai_core.graphs.smart_paraphrase import run_smart_paraphrase_llm
            return run_smart_paraphrase_llm(
                input_data.get("highlighted_text", ""),
                input_data.get("paragraph_text", ""),
            )

        return AIToolPolicy.execute(
            tool_name=self.name,
            version=self.version,
            func=_execute,
            input_data=input_data,
            user_id=user_id,
            use_cache=False,  # Allow test-time dynamic mocks
        )


smart_paraphrase_tool = SmartParaphraseTool()
register_ai_tool(smart_paraphrase_tool)
