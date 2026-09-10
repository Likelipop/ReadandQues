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
    
    # Force overrides for accessing dockerized services from host during evaluation
    os.environ["MONGO_URI"] = os.getenv("MONGO_HOST_URI", "mongodb://admin:changeme@localhost:27017/articlesDB?authSource=admin")
    os.environ["CHROMA_HOST"] = "localhost"
    os.environ["CHROMA_PORT"] = "8002"
    os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"

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

def save_evaluation_results(eval_result, output_name: str = "rag_triad_results.json"):
    """Extract metrics from evaluated test cases and save to JSON."""
    results_dir = PROJECT_ROOT / "evaluation" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    extracted_results = []
    test_results = getattr(eval_result, "test_results", eval_result)
    
    metrics_summary = {}
    
    for tr in test_results:
        tr_data = {
            "name": getattr(tr, "name", ""),
            "input": getattr(tr, "input", ""),
            "actual_output": getattr(tr, "actual_output", ""),
            "retrieval_context": getattr(tr, "retrieval_context", []),
            "success": getattr(tr, "success", False),
            "metrics": {}
        }
        metrics_data = getattr(tr, "metrics_data", []) or []
        for m in metrics_data:
            metric_name = getattr(m, "name", m.__class__.__name__)
            score = getattr(m, "score", None)
            threshold = getattr(m, "threshold", 0.7)
            success = getattr(m, "success", False)
            reason = getattr(m, "reason", None)
            error = getattr(m, "error", None)
            
            tr_data["metrics"][metric_name] = {
                "score": score,
                "threshold": threshold,
                "success": success,
                "reason": reason,
                "error": error
            }
            
            if metric_name not in metrics_summary:
                metrics_summary[metric_name] = {"scores": [], "passed": 0, "total": 0}
            metrics_summary[metric_name]["total"] += 1
            if score is not None:
                metrics_summary[metric_name]["scores"].append(score)
            if success:
                metrics_summary[metric_name]["passed"] += 1
                
        extracted_results.append(tr_data)
        
    summary_report = {
        "total_test_cases": len(extracted_results),
        "passed_test_cases": sum(1 for tr in extracted_results if tr.get("success", False)),
        "metrics_summary": {
            m_name: {
                "average_score": round(sum(data["scores"]) / len(data["scores"]), 4) if data["scores"] else 0.0,
                "pass_rate": f"{(data['passed'] / data['total'] * 100):.2f}%" if data["total"] > 0 else "0.00%",
                "passed": data["passed"],
                "total": data["total"]
            }
            for m_name, data in metrics_summary.items()
        },
        "results": extracted_results
    }
    
    output_path = results_dir / output_name
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Đã lưu kết quả đánh giá chi tiết tại: {output_path}")
    return summary_report
