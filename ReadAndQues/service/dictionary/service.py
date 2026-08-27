"""Dictionary Service using NLTK WordNet and comprehensive offline English lexicon for fast, authentic vocabulary lookup."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Comprehensive lexical dictionary for closed-class, grammatical, and common academic English words
COMMON_LEXICON: dict[str, dict[str, Any]] = {
    "the": {
        "word": "the",
        "found": True,
        "part_of_speech": "determiner / definite article",
        "lemma": "the",
        "definitions": [
            {
                "part_of_speech": "determiner",
                "definition": "Denoting one or more people or things already mentioned, assumed to be common knowledge, or specifically identified.",
                "examples": [
                    "The author presents a compelling argument in the passage.",
                    "She pointed to the main conclusion.",
                ],
                "synonyms": [],
                "antonyms": [],
            }
        ],
    },
    "a": {
        "word": "a",
        "found": True,
        "part_of_speech": "determiner / indefinite article",
        "lemma": "a",
        "definitions": [
            {
                "part_of_speech": "determiner",
                "definition": "Used when referring to someone or something for the first time in a text or not specifically identified.",
                "examples": [
                    "A new study explores the effects of sleep on memory.",
                    "He discovered a breakthrough method.",
                ],
                "synonyms": ["an", "one"],
                "antonyms": [],
            }
        ],
    },
    "an": {
        "word": "an",
        "found": True,
        "part_of_speech": "determiner / indefinite article",
        "lemma": "an",
        "definitions": [
            {
                "part_of_speech": "determiner",
                "definition": "The form of the indefinite article used before words beginning with a vowel sound.",
                "examples": ["An academic experiment was conducted across multiple universities."],
                "synonyms": ["a", "one"],
                "antonyms": [],
            }
        ],
    },
    "of": {
        "word": "of",
        "found": True,
        "part_of_speech": "preposition",
        "lemma": "of",
        "definitions": [
            {
                "part_of_speech": "preposition",
                "definition": "Expressing the relationship between a part and a whole, belonging, origin, or cause.",
                "examples": [
                    "The majority of participants showed measurable improvement.",
                    "The structure of the cell was analyzed.",
                ],
                "synonyms": ["concerning", "regarding", "pertaining to"],
                "antonyms": [],
            }
        ],
    },
    "to": {
        "word": "to",
        "found": True,
        "part_of_speech": "preposition / infinitive marker",
        "lemma": "to",
        "definitions": [
            {
                "part_of_speech": "preposition",
                "definition": "Expressing motion or direction toward a location, person, goal, or recipient; or used with a verb to form the infinitive.",
                "examples": [
                    "Researchers traveled to remote geological sites.",
                    "She wanted to understand the mechanism.",
                ],
                "synonyms": ["toward", "unto", "into"],
                "antonyms": [],
            }
        ],
    },
    "in": {
        "word": "in",
        "found": True,
        "part_of_speech": "preposition / adverb",
        "lemma": "in",
        "definitions": [
            {
                "part_of_speech": "preposition",
                "definition": "Expressing the situation of something enclosed or surrounded by something else, or indicating a period of time or condition.",
                "examples": [
                    "The findings were published in a scientific journal.",
                    "Significant progress was achieved in 2026.",
                ],
                "synonyms": ["inside", "within"],
                "antonyms": ["out", "outside"],
            }
        ],
    },
    "and": {
        "word": "and",
        "found": True,
        "part_of_speech": "conjunction",
        "lemma": "and",
        "definitions": [
            {
                "part_of_speech": "conjunction",
                "definition": "Used to connect words of the same part of speech, clauses, or sentences that are to be taken jointly.",
                "examples": ["Theory and empirical evidence both support the hypothesis."],
                "synonyms": ["along with", "as well as", "together with"],
                "antonyms": [],
            }
        ],
    },
    "is": {
        "word": "is",
        "found": True,
        "part_of_speech": "verb (copula / auxiliary)",
        "lemma": "be",
        "definitions": [
            {
                "part_of_speech": "verb",
                "definition": "Third person singular present of 'be': exist, occur, or have a specified quality, identity, or state.",
                "examples": ["Solar energy is an increasingly vital component of the modern power grid."],
                "synonyms": ["exists", "represents", "constitutes"],
                "antonyms": [],
            }
        ],
    },
    "are": {
        "word": "are",
        "found": True,
        "part_of_speech": "verb (copula / auxiliary)",
        "lemma": "be",
        "definitions": [
            {
                "part_of_speech": "verb",
                "definition": "Second person singular and plural present of 'be'.",
                "examples": ["Synaptic connections are dynamically reorganized during learning."],
                "synonyms": ["exist", "constitute"],
                "antonyms": [],
            }
        ],
    },
    "for": {
        "word": "for",
        "found": True,
        "part_of_speech": "preposition / conjunction",
        "lemma": "for",
        "definitions": [
            {
                "part_of_speech": "preposition",
                "definition": "Affecting, with with respect to, or in defense of; indicating the purpose, recipient, or duration of an action.",
                "examples": ["The algorithm was developed for natural language comprehension."],
                "synonyms": ["intended for", "serving"],
                "antonyms": [],
            }
        ],
    },
    "with": {
        "word": "with",
        "found": True,
        "part_of_speech": "preposition",
        "lemma": "with",
        "definitions": [
            {
                "part_of_speech": "preposition",
                "definition": "Accompanied by, in company with, or possessing a specified feature or instrument.",
                "examples": ["The experiment was carried out with high precision instruments."],
                "synonyms": ["alongside", "using", "by means of"],
                "antonyms": ["without"],
            }
        ],
    },
    "that": {
        "word": "that",
        "found": True,
        "part_of_speech": "pronoun / determiner / conjunction",
        "lemma": "that",
        "definitions": [
            {
                "part_of_speech": "pronoun",
                "definition": "Used to identify a specific person, thing, or statement; or introducing a subordinate clause.",
                "examples": ["The hypothesis that neural pathways remain malleable is widely accepted."],
                "synonyms": ["which"],
                "antonyms": [],
            }
        ],
    },
    "this": {
        "word": "this",
        "found": True,
        "part_of_speech": "pronoun / determiner",
        "lemma": "this",
        "definitions": [
            {
                "part_of_speech": "pronoun",
                "definition": "Referring to a specific person, thing, or concept close at hand or immediately discussed.",
                "examples": ["This investigation provides fresh insights into cognitive modeling."],
                "synonyms": [],
                "antonyms": ["that"],
            }
        ],
    },
    "pedagogical": {
        "word": "pedagogical",
        "found": True,
        "part_of_speech": "adjective",
        "lemma": "pedagogy",
        "definitions": [
            {
                "part_of_speech": "adjective",
                "definition": "Relating to the methods, theory, and principles of teaching and education.",
                "examples": ["The university adopted modern pedagogical frameworks for blended learning."],
                "synonyms": ["instructional", "educational", "academic", "didactic"],
                "antonyms": [],
            }
        ],
    },
    "mitigate": {
        "word": "mitigate",
        "found": True,
        "part_of_speech": "verb",
        "lemma": "mitigate",
        "definitions": [
            {
                "part_of_speech": "verb",
                "definition": "Make something less severe, serious, harmful, or painful.",
                "examples": ["Measures were taken to mitigate the risks associated with data privacy."],
                "synonyms": ["alleviate", "reduce", "diminish", "lessen", "attenuate"],
                "antonyms": ["aggravate", "worsen", "intensify"],
            }
        ],
    },
    "neuroplasticity": {
        "word": "neuroplasticity",
        "found": True,
        "part_of_speech": "noun",
        "lemma": "neuroplasticity",
        "definitions": [
            {
                "part_of_speech": "noun",
                "definition": "The ability of the brain to form and reorganize synaptic connections, especially in response to learning or experience.",
                "examples": ["Neuroplasticity allows adult polyglots to adapt to new linguistic patterns."],
                "synonyms": ["neural plasticity", "brain malleability", "cognitive adaptability"],
                "antonyms": [],
            }
        ],
    },
    "geothermal": {
        "word": "geothermal",
        "found": True,
        "part_of_speech": "adjective",
        "lemma": "geothermal",
        "definitions": [
            {
                "part_of_speech": "adjective",
                "definition": "Relating to or produced by the internal thermal heat of the earth.",
                "examples": ["Deep-sea geothermal energy can supply continuous baseload clean power."],
                "synonyms": ["hydrothermal", "terrestrial heat", "earth-energy"],
                "antonyms": [],
            }
        ],
    },
}

POS_MAP = {"n": "noun", "v": "verb", "a": "adjective", "s": "adjective", "r": "adverb"}

_WORDNET_INITIALIZED = False


def _ensure_wordnet():
    """Ensure WordNet corpus is downloaded and ready."""
    global _WORDNET_INITIALIZED
    if _WORDNET_INITIALIZED:
        return

    try:
        import nltk

        try:
            from nltk.corpus import wordnet as wn

            wn.synsets("test")
            _WORDNET_INITIALIZED = True
        except Exception:
            nltk.download("wordnet", quiet=True)
            nltk.download("omw-1.4", quiet=True)
            _WORDNET_INITIALIZED = True
    except Exception as e:
        logger.warning("Failed to initialize NLTK WordNet: %s", e)


def lookup_word(word: str) -> dict[str, Any]:
    """
    Look up an English word in offline lexicon and NLTK WordNet.
    Returns structured real definitions, parts of speech, examples, and synonyms.
    """
    cleaned_word = word.strip().lower()
    # Strip any trailing punctuation like commas, periods, quotes
    cleaned_word = cleaned_word.strip(".,;:\"'!?()[]{}")
    if not cleaned_word:
        return {"word": word, "found": False, "definitions": []}

    # Check common lexicon first
    if cleaned_word in COMMON_LEXICON:
        return COMMON_LEXICON[cleaned_word]

    _ensure_wordnet()

    try:
        from nltk.corpus import wordnet as wn

        synsets = wn.synsets(cleaned_word)
        if not synsets:
            # Try lemmatization across parts of speech
            for pos in ["n", "v", "a", "r"]:
                lemma = wn.morphy(cleaned_word, pos)
                if lemma and lemma != cleaned_word:
                    synsets = wn.synsets(lemma)
                    if synsets:
                        cleaned_word = lemma
                        break

        if not synsets:
            # If word is unknown, return graceful response without artificial boilerplate
            return {"word": word, "found": False, "definitions": []}

        definitions_list = []
        seen_definitions = set()
        primary_pos = None

        for syn in synsets[:5]:  # Top 5 most relevant synsets
            defn = syn.definition()
            if defn in seen_definitions:
                continue
            seen_definitions.add(defn)

            pos_char = syn.pos()
            pos_label = POS_MAP.get(pos_char, "noun")
            if not primary_pos:
                primary_pos = pos_label

            synonyms = set()
            antonyms = set()

            for lemma_obj in syn.lemmas():
                lemma_name = lemma_obj.name().replace("_", " ")
                if lemma_name.lower() != cleaned_word:
                    synonyms.add(lemma_name)
                for ant in lemma_obj.antonyms():
                    antonyms.add(ant.name().replace("_", " "))

            definitions_list.append(
                {
                    "part_of_speech": pos_label,
                    "definition": defn.capitalize(),
                    "examples": [ex.capitalize() for ex in syn.examples()],
                    "synonyms": list(synonyms)[:5],
                    "antonyms": list(antonyms)[:3],
                }
            )

        return {
            "word": word,
            "found": True,
            "lemma": cleaned_word,
            "part_of_speech": primary_pos or "noun",
            "definitions": definitions_list,
        }

    except Exception as e:
        logger.error("Error looking up word in WordNet: %s", e)
        return {"word": word, "found": False, "definitions": []}
