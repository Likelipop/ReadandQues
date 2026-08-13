import logging
from typing import Any, Dict, Optional

from service.ai_core.graphs.ask_article.graph import run_ask_article_flow
from service.ai_core.platform import AITool, AIToolPolicy, AIToolRunResult, register_ai_tool

logger = logging.getLogger(__name__)


class AskArticleTool(AITool):
    name = "ask_article"
    version = "1.0.0"
    model_profile = "precise"

    def run(self, input_data: Dict[str, Any], user_id: Optional[int] = None) -> AIToolRunResult:
        article_text = input_data.get("article_text", "")
        question = input_data.get("question", "")

        def _execute():
            return run_ask_article_flow(article_text=article_text, question=question)

        return AIToolPolicy.execute(
            tool_name=self.name,
            version=self.version,
            func=_execute,
            input_data=input_data,
            user_id=user_id,
            use_cache=False,
        )


ask_article_tool = AskArticleTool()
register_ai_tool(ask_article_tool)
