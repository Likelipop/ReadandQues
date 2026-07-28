from typing import List
from pydantic import BaseModel, Field

class PhraseAlternative(BaseModel):
    original_text: str = Field(description="The key phrase extracted from the text")
    alternatives: List[str] = Field(description="2-3 alternative ways to express the same idea")

class ParaphraseOutput(BaseModel):
    phrases: List[PhraseAlternative] = Field(description="List of extracted phrases and their alternatives")
