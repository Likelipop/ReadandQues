import unittest

from service.ai_core.platform import get_ai_tool
from service.ai_core.graphs.explained.graph import (
    stream_explained_tokens,
    run_explained_flow,
)


class ExplainedGraphTests(unittest.TestCase):
    def test_explained_tool_registered(self):
        tool = get_ai_tool("explained")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "explained")

    def test_run_explained_flow(self):
        res = run_explained_flow(
            phrase="pedagogical frameworks",
            paragraph_context="Universities are adopting blended pedagogical frameworks.",
        )
        self.assertIn("phrase", res)
        self.assertIn("summary", res)
        self.assertIn("detailed_explanation", res)

    def test_stream_explained_tokens(self):
        tokens = list(stream_explained_tokens(
            phrase="mitigate risks",
            paragraph_context="The strategy aimed to mitigate risks across departments.",
        ))
        self.assertGreater(len(tokens), 0)
        full_text = "".join(tokens)
        self.assertIn("In Simple Words", full_text)
