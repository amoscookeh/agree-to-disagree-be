"""llm-as-judge evaluation script for research quality"""

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from deepeval import evaluate
from deepeval.test_case import LLMTestCase

from scripts.evaluators import BalanceMetric, CitationMetric, GroundednessMetric
from src.agents.graph import research_graph
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

TEST_QUERIES = [
    "What are perspectives on raising the federal minimum wage to $15?",
    "How do different groups view the Affordable Care Act?",
    "What are the arguments for and against gun control legislation?",
    "Should the US adopt universal healthcare?",
    "What are perspectives on immigration reform?",
]


async def run_research(query: str) -> dict | None:
    """run research graph and return final report"""
    try:
        logger.info(f"running research for: {query}")

        initial_state = {
            "query": query,
            "thread_id": f"eval_{datetime.now(UTC).timestamp()}",
        }

        config = {"configurable": {"thread_id": initial_state["thread_id"]}}

        result = await research_graph.ainvoke(initial_state, config)

        report = result.get("report")
        if not report:
            logger.warning(f"no report generated for query: {query}")
            return None

        logger.info(
            f"research complete: {len(result.get('citations', []))} citations, "
            f"{len(result.get('agreements', []))} agreements, "
            f"{len(result.get('disagreements', []))} disagreements"
        )

        return report

    except Exception as e:
        logger.error(f"research failed for query '{query}': {e}")
        return None


async def evaluate_report(query: str, report: dict) -> dict:
    """evaluate report using deepeval metrics"""

    test_case = LLMTestCase(input=query, actual_output=json.dumps(report))

    metrics = [
        BalanceMetric(threshold=0.5),
        GroundednessMetric(threshold=0.7),
        CitationMetric(threshold=0.8),
    ]

    evaluate(test_cases=[test_case], metrics=metrics)

    scores = {
        "balance": {
            "score": metrics[0].score,
            "reasoning": metrics[0].reason,
            "success": metrics[0].is_successful(),
        },
        "groundedness": {
            "score": metrics[1].score,
            "reasoning": metrics[1].reason,
            "success": metrics[1].is_successful(),
        },
        "citation": {
            "score": metrics[2].score,
            "reasoning": metrics[2].reason,
            "success": metrics[2].is_successful(),
        },
        "average": (metrics[0].score + metrics[1].score + metrics[2].score) / 3,
    }

    return scores


async def run_evaluation():
    """run evaluation on all test queries"""
    results = []

    for query in TEST_QUERIES:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"evaluating: {query}")
        logger.info(f"{'=' * 60}")

        report = await run_research(query)

        if not report:
            logger.warning(f"skipping evaluation for failed query: {query}")
            results.append(
                {
                    "query": query,
                    "error": "research failed",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
            continue

        scores = await evaluate_report(query, report)

        results.append(
            {
                "query": query,
                "scores": scores,
                "report_metadata": {
                    "citations_count": len(report.get("citations", [])),
                    "agreements_count": len(report.get("agreements", [])),
                    "disagreements_count": len(report.get("disagreements", [])),
                    "uncertainties_count": len(report.get("uncertainties", [])),
                    "cycles_used": report.get("metadata", {}).get("cycles_used", 0),
                },
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        logger.info(f"balance: {scores['balance']['score']:.2f}")
        logger.info(f"groundedness: {scores['groundedness']['score']:.2f}")
        logger.info(f"citation: {scores['citation']['score']:.2f}")
        logger.info(f"average: {scores['average']:.2f}")

    print_results(results)
    save_results(results)


def print_results(results: list):
    """pretty print results to console"""
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)

    successful_results = [r for r in results if "scores" in r]

    for r in successful_results:
        print(f"\nquery: {r['query'][:50]}...")
        print(
            f"  balance:      {r['scores']['balance']['score']:.2f} ✓"
            if r["scores"]["balance"]["success"]
            else f"  balance:      {r['scores']['balance']['score']:.2f} ✗"
        )
        print(
            f"  groundedness: {r['scores']['groundedness']['score']:.2f} ✓"
            if r["scores"]["groundedness"]["success"]
            else f"  groundedness: {r['scores']['groundedness']['score']:.2f} ✗"
        )
        print(
            f"  citation:     {r['scores']['citation']['score']:.2f} ✓"
            if r["scores"]["citation"]["success"]
            else f"  citation:     {r['scores']['citation']['score']:.2f} ✗"
        )
        print(f"  average:      {r['scores']['average']:.2f}")

    if not successful_results:
        print("\nno successful evaluations")
        return

    avg_balance = sum(
        r["scores"]["balance"]["score"] for r in successful_results
    ) / len(successful_results)
    avg_ground = sum(
        r["scores"]["groundedness"]["score"] for r in successful_results
    ) / len(successful_results)
    avg_cite = sum(r["scores"]["citation"]["score"] for r in successful_results) / len(
        successful_results
    )

    print("\n" + "-" * 60)
    print("OVERALL AVERAGES:")
    print(f"  balance:      {avg_balance:.2f}")
    print(f"  groundedness: {avg_ground:.2f}")
    print(f"  citation:     {avg_cite:.2f}")
    print(f"  TOTAL:        {(avg_balance + avg_ground + avg_cite) / 3:.2f}")

    failed_count = len(results) - len(successful_results)
    if failed_count > 0:
        print(f"\n  failed queries: {failed_count}/{len(results)}")


def save_results(results: list):
    """save results to json file"""
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    filename = f"eval_results_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
    filepath = results_dir / filename

    with open(filepath, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nresults saved to {filepath}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
