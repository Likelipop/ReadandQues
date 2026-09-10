import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from deepeval.models import AzureOpenAIModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def setup_evaluation_environment():
    """Load env vars and set DB overrides for external test execution."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    load_dotenv(PROJECT_ROOT / ".env")
    
    # Overrides for accessing dockerized services from host
    os.environ.setdefault("MONGO_URI", "mongodb://admin:changeme@localhost:27017/articlesDB?authSource=admin")
    os.environ.setdefault("CHROMA_HOST", "localhost")
    os.environ.setdefault("CHROMA_PORT", "8002")

def setup_judge_model():
    """Initialize Azure OpenAI judge model for DeepEval."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").replace("/openai/v1", "")
    return AzureOpenAIModel(
        model=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-5-mini"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        base_url=endpoint,
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )

def load_dataset(dataset_name: str = "rag_eval_dataset.json") -> list[dict]:
    """Load a JSON dataset from the evaluation/datasets directory."""
    dataset_path = PROJECT_ROOT / "evaluation" / "datasets" / dataset_name
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_evaluation_results(test_cases, output_name: str = "rag_eval_results.json"):
    """Extract metrics from evaluated test cases and save to JSON."""
    results_dir = PROJECT_ROOT / "evaluation" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    extracted_results = []
    for tc in test_cases:
        tc_data = {
            "input": tc.input,
            "actual_output": tc.actual_output,
            "metrics": {}
        }
        if hasattr(tc, 'metrics'):
            for m in tc.metrics:
                tc_data["metrics"][m.__class__.__name__] = {
                    "score": getattr(m, 'score', None),
                    "reason": getattr(m, 'reason', None),
                    "success": getattr(m, 'success', getattr(m, 'is_successful', None))
                }
        extracted_results.append(tc_data)
        
    output_path = results_dir / output_name
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extracted_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Đã lưu kết quả đánh giá chi tiết tại: {output_path}")
