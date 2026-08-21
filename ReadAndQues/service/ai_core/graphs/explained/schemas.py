from typing import Any, TypedDict
from pydantic import BaseModel, Field


class KeyTerm(BaseModel):
    term: str = Field(description="Key word from the phrase.")
    meaning: str = Field(description="Brief meaning of the term in context.")


class ExplainedOutput(BaseModel):
    phrase: str = Field(description="The phrase or sentence being explained.")
    summary: str = Field(description="A concise 1-sentence explanation of what this phrase means in this context.")
    detailed_explanation: str = Field(description="Clear academic explanation of the phrase and how it relates to the paragraph context.")
    simplified_version: str = Field(description="A simplified, plain English rewrite of the phrase.")
    key_terms: list[KeyTerm] = Field(default_factory=list, description="Key vocabulary terms in the phrase with their contextual meanings.")


class ExplainedState(TypedDict):
    phrase: str
    paragraph_context: str
    summary: str
    detailed_explanation: str
    simplified_version: str
    key_terms: list[dict[str, str]]
    retry_count: int
