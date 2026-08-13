from pydantic import BaseModel, Field
from typing import TypedDict

class SmartParaphraseOutput(BaseModel):
    expanded_text: str = Field(description="Must be EXACTLY the same as the highlighted text, character for character.")
    paraphrased_text: str = Field(description="The in-place paraphrase or synonym for the highlighted text.")
    explanation: str = Field(description="Explanation of why this paraphrase is accurate.")

class ValidatorOutput(BaseModel):
    is_valid: bool = Field(description="True if the paraphrase perfectly maintains original meaning without extra or missing details. False otherwise.")
    feedback: str = Field(description="If is_valid is False, provide specific feedback on what details were missing or hallucinated.")

class SmartParaphraseState(TypedDict):
    highlighted_text: str
    paragraph_context: str
    expanded_text: str
    paraphrased_text: str
    explanation: str
    is_valid: bool
    validation_feedback: str
    retry_count: int
