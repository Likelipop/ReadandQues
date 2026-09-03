import unittest

from ai_service.quiz_generator import stream_explained_tokens


class ExplainedStreamingTests(unittest.TestCase):
    def test_stream_term_tokens(self):
        tokens = list(
            stream_explained_tokens(
                phrase="pedagogy",
                paragraph_context="Universities are adopting blended pedagogy models.",
            )
        )
        self.assertGreater(len(tokens), 0)
        full_text = "".join(tokens)
        self.assertIn("pedagogy", full_text.lower())

    def test_stream_sentence_tokens(self):
        sentence = "Deep-sea geothermal extraction has emerged as an exceptionally viable alternative."
        tokens = list(
            stream_explained_tokens(
                phrase=sentence,
                paragraph_context=sentence,
            )
        )
        self.assertGreater(len(tokens), 0)
        full_text = "".join(tokens)
        self.assertIn("In Simple Words", full_text)
