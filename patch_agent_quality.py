import re

with open("evaluation/test_agent_quality.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace _get_judge_model and its call
target = """def _get_judge_model():
    \"\"\"
    Initialize the LLM judge for DeepEval metrics.
    Uses Azure OpenAI (same as project) so no separate OPENAI_API_KEY needed.
    \"\"\"
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")

    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_deployment = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-5-mini")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

    # Clean endpoint (remove /openai/v1 suffix if present)
    if azure_endpoint.endswith("/openai/v1"):
        azure_endpoint = azure_endpoint.replace("/openai/v1", "")

    if azure_key and azure_endpoint:
        from deepeval.models import AzureOpenAIModel
        logger.info(f"Using Azure OpenAI as judge: {azure_deployment} @ {azure_endpoint}")
        return AzureOpenAIModel(
            model=azure_deployment,
            api_key=azure_key,
            base_url=azure_endpoint,
            api_version=api_version,
        )

    # Fallback: try standard OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        logger.info("Using standard OpenAI as judge")
        return None  # DeepEval uses OpenAI by default when model=None

    raise RuntimeError(
        "No LLM judge configured. Set AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT "
        "or OPENAI_API_KEY in your environment."
    )


JUDGE_MODEL = _get_judge_model()"""

replacement = """from evaluation.utils import setup_evaluation_environment, setup_judge_model

setup_evaluation_environment()
JUDGE_MODEL = setup_judge_model()"""

content = content.replace(target, replacement)

# Replace DATASET_PATH
target_dataset = """def load_golden_dataset() -> list[dict[str, Any]]:
    \"\"\"
    Load the static JSON test cases.
    Each item has: input, expected_output, retrieval_context.
    \"\"\"
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")
    
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)"""

replacement_dataset = """from evaluation.utils import load_dataset
def load_golden_dataset() -> list[dict[str, Any]]:
    \"\"\"
    Load the static JSON test cases.
    Each item has: input, expected_output, retrieval_context.
    \"\"\"
    return load_dataset("agent_golden_dataset.json")"""

content = content.replace(target_dataset, replacement_dataset)

with open("evaluation/test_agent_quality.py", "w", encoding="utf-8") as f:
    f.write(content)
