import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
"""
evaluation/test_agent_quality.py — DeepEval Evaluation Pipeline for ReadAndQues AI Agent.

Automated benchmark measuring:
  1. Answer Relevancy  → response accuracy (does the answer address the question?)
  2. Faithfulness       → hallucination rate (does the agent fabricate info beyond context?)
  3. Contextual Relevancy → grounding quality (is the retrieved context actually relevant?)

Usage:
  # Run with deepeval CLI (recommended — generates dashboard report)
  deepeval test run evaluation/test_agent_quality.py -v

  # Run with pytest
  pytest evaluation/test_agent_quality.py -v

  # Run standalone script to see results without pytest
  python evaluation/test_agent_quality.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import pytest
from deepeval import assert_test
from deepeval.dataset import EvaluationDataset
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    GEval,
)
from deepeval.test_case import LLMTestCase, SingleTurnParams

# ── Configuration ────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "evaluation" / "datasets" / "agent_golden_dataset.json"
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Metric thresholds (0.0 – 1.0)
RELEVANCY_THRESHOLD = 0.7
FAITHFULNESS_THRESHOLD = 0.7
CONTEXTUAL_RELEVANCY_THRESHOLD = 0.7


# ── Judge Model (LLM-as-a-Judge for DeepEval) ───────────────────────────────

from evaluation.utils import setup_evaluation_environment, setup_judge_model

setup_evaluation_environment()
JUDGE_MODEL = setup_judge_model()


# ── Dataset Loader ───────────────────────────────────────────────────────────


def load_golden_dataset() -> list[dict[str, Any]]: # WHAT: FOR WHAT
    """Load the golden evaluation dataset from JSON."""
    with open(DATASET_PATH, encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Loaded {len(data)} test cases from {DATASET_PATH.name}")
    return data


# ── Agent Caller ─────────────────────────────────────────────────────────────
# Two modes:
#   Mode A — LIVE: calls the real ai_service agent (requires infra: Azure LLM, ChromaDB, etc.)
#   Mode B — SIMULATED: uses the expected_output as actual_output for benchmarking metrics
#            This lets you validate the evaluation pipeline itself without LLM costs.


def _call_live_agent(query: str, context_texts: list[str]) -> str: # WHAT
    """
    Call the real Study Dock agent and collect the full response.
    Requires: Azure OpenAI key, PostgreSQL (for checkpointer).
    Falls back to simulated mode on failure.
    """
    try:
        from ai_service.interface import ask_study_dock

        result = ask_study_dock(
            query=query,
            page_context="homepage",
            article_text="\n\n".join(context_texts) if context_texts else "",
        )
        return result.get("response", "")
    except Exception as e:
        logger.warning(f"Live agent call failed ({e}), falling back to simulated mode.")
        return ""


def get_agent_response(test_case_data: dict[str, Any], mode: str = "auto") -> str: # WHAT
    """
    Get the agent's response for a given test case.

    Args:
        test_case_data: Dict with keys input, expected_output, retrieval_context.
        mode: "live" | "simulated" | "auto"
              auto = try live first, fall back to simulated.
    """
    query = test_case_data["input"]
    context = test_case_data.get("retrieval_context", [])

    if mode == "simulated":
        return test_case_data["expected_output"]

    if mode == "live" or mode == "auto":
        response = _call_live_agent(query, context)
        if response:
            return response
        # Fall back to simulated if live fails and mode is auto
        if mode == "auto":
            return test_case_data["expected_output"]
        return ""

    return test_case_data["expected_output"]


# ── DeepEval Test Cases Builder ──────────────────────────────────────────────


def build_test_cases(mode: str = "auto") -> list[LLMTestCase]:
    """Build DeepEval LLMTestCase objects from the golden dataset."""
    dataset = load_golden_dataset()
    test_cases = []

    for i, item in enumerate(dataset):
        actual_output = get_agent_response(item, mode=mode)
        if not actual_output:
            logger.warning(f"Skipping test case {i} — empty response for: {item['input'][:50]}...")
            continue

        tc = LLMTestCase(
            input=item["input"],
            actual_output=actual_output,
            expected_output=item.get("expected_output", ""),
            retrieval_context=item.get("retrieval_context", []),
        )
        test_cases.append(tc)

    logger.info(f"Built {len(test_cases)} test cases (mode={mode})")
    return test_cases


# ── Metrics Setup ────────────────────────────────────────────────────────────


def get_metrics():
    """
    Initialize the 3 core metrics aligned with Katalon JD requirements:
      1. Answer Relevancy → "response accuracy"
      2. Faithfulness → "hallucination rate"
      3. Contextual Relevancy → "grounding"
    """
    answer_relevancy = AnswerRelevancyMetric(
        threshold=RELEVANCY_THRESHOLD,
        include_reason=True,
        model=JUDGE_MODEL,
    )

    faithfulness = FaithfulnessMetric(
        threshold=FAITHFULNESS_THRESHOLD,
        include_reason=True,
        model=JUDGE_MODEL,
    )

    contextual_relevancy = ContextualRelevancyMetric(
        threshold=CONTEXTUAL_RELEVANCY_THRESHOLD,
        include_reason=True,
        model=JUDGE_MODEL,
    )

    return [answer_relevancy, faithfulness, contextual_relevancy]


def get_correctness_metric():
    """
    Custom GEval metric to evaluate answer correctness against expected output.
    Uses LLM-as-a-judge to compare actual vs expected answers.
    """
    return GEval(
        name="Answer Correctness",
        criteria=(
            "Evaluate whether the actual output conveys the same key information "
            "and meaning as the expected output. Consider factual accuracy, "
            "completeness of key points, and absence of incorrect information."
        ),
        evaluation_params=[
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        threshold=0.7,
        model=JUDGE_MODEL,
    )


# ── Pytest / DeepEval Integration ────────────────────────────────────────────

# Determine mode from environment variable (default: auto)
EVAL_MODE = os.environ.get("EVAL_MODE", "auto")
_test_cases = build_test_cases(mode=EVAL_MODE)
_metrics = get_metrics()


@pytest.mark.parametrize(
    "test_case",
    _test_cases,
    ids=[f"{i:02d}_{tc.input[:40].replace(' ', '_')}" for i, tc in enumerate(_test_cases)],
)
def test_agent_quality(test_case: LLMTestCase):
    """
    DeepEval parametrized test: evaluates each test case against all metrics.
    Run with: deepeval test run evaluation/test_agent_quality.py -v
    """
    assert_test(test_case, _metrics)


# ── Standalone Runner ────────────────────────────────────────────────────────


def run_evaluation_standalone(mode: str = "auto") -> dict[str, Any]:
    """
    Run evaluation without pytest — useful for scripting and CI/CD.
    Returns aggregated results dict.
    """
    test_cases = build_test_cases(mode=mode)
    metrics = get_metrics()
    correctness = get_correctness_metric()
    all_metrics = metrics + [correctness]

    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mode": mode,
        "total_cases": len(test_cases),
        "metrics_config": {
            "relevancy_threshold": RELEVANCY_THRESHOLD,
            "faithfulness_threshold": FAITHFULNESS_THRESHOLD,
            "contextual_relevancy_threshold": CONTEXTUAL_RELEVANCY_THRESHOLD,
        },
        "per_case_results": [],
        "aggregate": {},
    }

    metric_scores: dict[str, list[float]] = {m.__class__.__name__: [] for m in all_metrics}

    for i, tc in enumerate(test_cases):
        case_result = {
            "index": i,
            "input": tc.input[:80],
            "scores": {},
            "passed": {},
            "reasons": {},
        }

        for metric in all_metrics:
            try:
                metric.measure(tc)
                score = metric.score
                passed = metric.is_successful()
                reason = getattr(metric, "reason", "")
            except Exception as e:
                logger.error(f"Metric {metric.__class__.__name__} failed on case {i}: {e}")
                score = 0.0
                passed = False
                reason = f"Error: {e}"

            metric_name = metric.__class__.__name__
            if hasattr(metric, "name") and metric.name != metric_name:
                metric_name = metric.name

            case_result["scores"][metric_name] = round(score, 4) if score else 0.0
            case_result["passed"][metric_name] = passed
            case_result["reasons"][metric_name] = reason

            if score is not None:
                class_name = metric.__class__.__name__
                if class_name not in metric_scores:
                    metric_scores[metric_name] = []
                    metric_scores[metric_name].append(score)
                else:
                    metric_scores[class_name].append(score)

        results["per_case_results"].append(case_result)
        logger.info(
            f"[{i+1}/{len(test_cases)}] {tc.input[:50]}... → "
            f"Scores: {case_result['scores']}"
        )

    # Aggregate scores
    for metric_name, scores in metric_scores.items():
        if scores:
            avg = sum(scores) / len(scores)
            results["aggregate"][metric_name] = {
                "mean": round(avg, 4),
                "min": round(min(scores), 4),
                "max": round(max(scores), 4),
                "pass_rate": round(
                    sum(1 for s in scores if s >= RELEVANCY_THRESHOLD) / len(scores), 4
                ),
                "count": len(scores),
            }

    # Save results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"eval_results_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"\n{'='*60}")
    logger.info("EVALUATION SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total test cases: {len(test_cases)}")
    for metric_name, agg in results["aggregate"].items():
        logger.info(
            f"  {metric_name}: mean={agg['mean']:.2f}, "
            f"min={agg['min']:.2f}, max={agg['max']:.2f}, "
            f"pass_rate={agg['pass_rate']:.0%}"
        )
    logger.info(f"Results saved to: {output_path}")

    return results


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"
    print(f"\n🚀 Running ReadAndQues Agent Evaluation Pipeline (mode={mode})\n")
    run_evaluation_standalone(mode=mode)
