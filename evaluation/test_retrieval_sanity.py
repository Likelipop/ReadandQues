"""
evaluation/test_retrieval_sanity.py — Pre-Flight Retrieval Sanity Gate.

Guarantees that 100% of questions in the evaluation dataset successfully retrieve
relevant chunks from ChromaDB and BM25 before running expensive DeepEval judge evaluations.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.utils import load_dataset, setup_evaluation_environment

setup_evaluation_environment()

from ai_service.rag.agents.news_agent import retrieve_and_rerank_context


def run_sanity_gate(dataset_name: str = "rag_eval_dataset.json") -> bool:
    print(f"🚀 Running Pre-Flight Retrieval Sanity Gate on '{dataset_name}'...")
    dataset = load_dataset(dataset_name)
    total_questions = len(dataset)
    print(f"📋 Total test questions: {total_questions}\n")

    failed_retrievals = []
    target_matches = 0

    for i, item in enumerate(dataset):
        query = item["input"]
        target_aid = item.get("target_article_id")
        
        _, citations, chunks = retrieve_and_rerank_context(query)
        chunk_count = len(chunks)

        if chunk_count == 0:
            print(f"❌ [{i+1:02d}/{total_questions}] FAILED: 0 chunks retrieved! Query: {query}")
            failed_retrievals.append(query)
            continue

        chunk_aids = [c.get("metadata", {}).get("article_id") for c in chunks]
        has_target = target_aid in chunk_aids if target_aid else True
        if has_target:
            target_matches += 1

        top_title = chunks[0].get("metadata", {}).get("title", "Unknown")
        print(f"✅ [{i+1:02d}/{total_questions}] Chunks: {chunk_count} | Target Found: {has_target} | Top: {top_title[:50]}...")

    print("\n" + "=" * 60)
    print(f"📊 SANITY GATE RESULTS:")
    print(f"   • Total Questions: {total_questions}")
    print(f"   • Successful Retrievals: {total_questions - len(failed_retrievals)}/{total_questions} ({(total_questions - len(failed_retrievals))/total_questions*100:.1f}%)")
    print(f"   • Target Article in Top-K: {target_matches}/{total_questions} ({target_matches/total_questions*100:.1f}%)")
    print("=" * 60)

    if failed_retrievals:
        print(f"\n❌ Pre-Flight Gate FAILED: {len(failed_retrievals)} question(s) returned 0 chunks.")
        return False

    print("\n🎉 Pre-Flight Gate PASSED! 100% of questions retrieved chunks successfully. Safe to run DeepEval.")
    return True


if __name__ == "__main__":
    success = run_sanity_gate()
    sys.exit(0 if success else 1)
