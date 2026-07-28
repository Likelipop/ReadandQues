from pathlib import Path
from langchain_core.prompts import PromptTemplate

_PROMPTS_DIR = Path(__file__).resolve().parent

def load_prompt(filename: str) -> str:
    with open(_PROMPTS_DIR / filename, "r", encoding="utf-8") as f:
        return f.read()

def build_paraphrase_prompt() -> PromptTemplate:
    template = load_prompt("paraphraser.md")
    return PromptTemplate(template=template, input_variables=["text"])
