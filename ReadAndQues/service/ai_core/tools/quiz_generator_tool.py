import logging
from typing import Any, Dict, Optional

from service.ai_core.graphs.question_generator.graph import run_question_generator_flow
from service.ai_core.platform import AITool, AIToolPolicy, AIToolRunResult, register_ai_tool

logger = logging.getLogger(__name__)


class QuizGeneratorTool(AITool):
    name = "quiz_generator"
    version = "1.0.0"
    model_profile = "default"

    def run(self, input_data: Dict[str, Any], user_id: Optional[int] = None) -> AIToolRunResult:
        original_text = input_data.get("original_text", "")

        def _execute():
            return run_question_generator_flow(original_text)

        return AIToolPolicy.execute(
            tool_name=self.name,
            version=self.version,
            func=_execute,
            input_data=input_data,
            user_id=user_id,
            use_cache=False,
        )


quiz_generator_tool = QuizGeneratorTool()
register_ai_tool(quiz_generator_tool)
