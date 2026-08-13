from unittest import TestCase
from unittest.mock import Mock, patch

from service.ai_core.platform import (
    AITool,
    AIToolPolicy,
    AIToolRunResult,
    ModelGateway,
    get_ai_tool,
    register_ai_tool,
)
from service.ai_core.platform.policy import clear_ai_cache
import service.ai_core.tools  # noqa: F401


class AIPlatformTests(TestCase):
    def setUp(self):
        clear_ai_cache()

    def tearDown(self):
        clear_ai_cache()

    def test_model_gateway_profiles(self):
        with patch("service.ai_core.platform.gateway.default_router.get_llm") as mock_get_llm:
            mock_get_llm.return_value = Mock()
            llm = ModelGateway.get_llm("precise", temperature=0.1)
            self.assertIsNotNone(llm)
            mock_get_llm.assert_called_once_with(temperature=0.1)

    def test_ai_tool_registry_and_invocation(self):
        tool = get_ai_tool("smart_paraphrase")
        self.assertEqual(tool.name, "smart_paraphrase")
        self.assertEqual(tool.version, "1.0.0")

        quiz_tool = get_ai_tool("quiz_generator")
        self.assertEqual(quiz_tool.name, "quiz_generator")

    def test_ai_tool_policy_creates_run_result(self):
        def dummy_func():
            return {"summary": "dummy"}

        res = AIToolPolicy.execute(
            tool_name="dummy_tool",
            version="1.0.0",
            func=dummy_func,
            input_data={"text": "hello"},
            use_cache=False,
        )

        self.assertTrue(res.run_id.startswith("run_"))
        self.assertEqual(res.status, "completed")
        self.assertEqual(res.output, {"summary": "dummy"})

    def test_smart_paraphrase_tool_execution(self):
        tool = get_ai_tool("smart_paraphrase")
        with patch("service.ai_core.graphs.smart_paraphrase.run_smart_paraphrase_llm") as mock_flow:
            mock_flow.return_value = {
                "expanded_text": "expanded",
                "paraphrased_text": "paraphrased",
            }
            res = tool.run({"highlighted_text": "text_abc", "paragraph_text": "full text abc"})
            self.assertEqual(res.status, "completed")
            self.assertEqual(res.output["paraphrased_text"], "paraphrased")
