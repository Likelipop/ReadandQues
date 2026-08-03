import os
from langchain_core.prompts import PromptTemplate

current_dir = os.path.dirname(os.path.abspath(__file__))

def get_generator_prompt():
    with open(os.path.join(current_dir, 'generator.md'), 'r') as f:
        template = f.read()
    return PromptTemplate.from_template(template)

def get_validator_prompt():
    with open(os.path.join(current_dir, 'validator.md'), 'r') as f:
        template = f.read()
    return PromptTemplate.from_template(template)
