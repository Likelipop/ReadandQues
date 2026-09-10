import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import os
from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.metrics import (
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    AnswerRelevancyMetric
)

from evaluation.utils import (
    setup_evaluation_environment,
    setup_judge_model,
    load_dataset,
    save_evaluation_results
)

# Setup environment before importing project logic that requires env vars
setup_evaluation_environment()
from ai_service.rag.agents.news_agent import run_news_agent, retrieve_and_rerank_context

def run_evaluation():
    print("🚀 Bắt đầu đánh giá RAG Triad...")
    judge = setup_judge_model()
    dataset = load_dataset()
    
    # 1. Khởi tạo 3 Metrics của RAG Triad
    metrics = [
        ContextualRelevancyMetric(threshold=0.7, model=judge, include_reason=True),
        FaithfulnessMetric(threshold=0.7, model=judge, include_reason=True),
        AnswerRelevancyMetric(threshold=0.7, model=judge, include_reason=True)
    ]
    
    test_cases = []
    
    for idx, item in enumerate(dataset, 1):
        query = item["input"]
        print(f"\n[{idx}/{len(dataset)}] ❓ Đang xử lý: {query}")
        
        _, _, retrieved_chunks = retrieve_and_rerank_context(query)
        retrieval_context = [chunk.get("text", "") for chunk in retrieved_chunks]
        
        agent_result = run_news_agent(query)
        actual_output = agent_result.answer
        
        test_case = LLMTestCase(
            input=query,
            actual_output=actual_output,
            retrieval_context=retrieval_context
        )
        test_cases.append(test_case)
        print(f"[{idx}/{len(dataset)}] ✅ Đã sinh xong câu trả lời.")

    # 3. Chấm điểm bằng DeepEval
    print("\n⚖️ Đang để LLM Judge chấm điểm (có thể mất vài phút)...")
    eval_result = evaluate(test_cases=test_cases, metrics=metrics)
    
    # 4. Lưu kết quả ra file JSON
    save_evaluation_results(eval_result, "rag_triad_results.json")
    
    print("\n🎉 Đã hoàn tất đánh giá!")

if __name__ == "__main__":
    run_evaluation()
