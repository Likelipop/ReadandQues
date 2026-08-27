from unittest import TestCase
from unittest.mock import Mock, patch

import service.ai_core.tools  # noqa: F401
from service.ai_core.platform import (
    AIToolPolicy,
    ModelGateway,
    get_ai_tool,
)
from service.ai_core.platform.policy import clear_ai_cache


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
        tool = get_ai_tool("explained")
        self.assertEqual(tool.name, "explained")
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

    def test_explained_tool_execution(self):
        tool = get_ai_tool("explained")
        with patch("service.ai_core.graphs.run_explained_flow") as mock_flow:
            mock_flow.return_value = {
                "phrase": "quantum",
                "detailed_explanation": "detailed explanation of quantum",
            }
            res = tool.run({"phrase": "quantum", "paragraph_context": "quantum mechanics"})
            self.assertEqual(res.status, "completed")
            self.assertEqual(res.output["detailed_explanation"], "detailed explanation of quantum")
