"""quick test script for evaluators without running full research"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from deepeval.test_case import LLMTestCase

from scripts.evaluators import BalanceMetric, CitationMetric, GroundednessMetric

MOCK_REPORT = {
    "summary": "The debate over raising the federal minimum wage to $15 involves economic and social considerations. Proponents argue it would reduce poverty and stimulate the economy, while opponents worry about job losses and increased costs for small businesses.",
    "claim_a": {
        "stance": "progressive",
        "title": "Support for $15 Minimum Wage",
        "evidence": [
            {
                "claim": "Raising minimum wage would lift millions out of poverty",
                "source": "Economic Policy Institute",
                "url": "https://example.com/epi-study",
                "confidence": 0.85,
            },
            {
                "claim": "Higher wages lead to increased consumer spending",
                "source": "Center for American Progress",
                "url": "https://example.com/cap-report",
                "confidence": 0.8,
            },
            {
                "claim": "Studies show minimal job loss from wage increases",
                "source": "UC Berkeley Labor Center",
                "url": "https://example.com/berkeley-study",
                "confidence": 0.75,
            },
        ],
    },
    "claim_b": {
        "stance": "conservative",
        "title": "Opposition to $15 Minimum Wage",
        "evidence": [
            {
                "claim": "Small businesses cannot afford higher wages",
                "source": "National Federation of Independent Business",
                "url": "https://example.com/nfib-survey",
                "confidence": 0.8,
            },
            {
                "claim": "Wage increases lead to automation and job cuts",
                "source": "American Enterprise Institute",
                "url": "https://example.com/aei-analysis",
                "confidence": 0.75,
            },
            {
                "claim": "Regional cost of living differences make federal mandate problematic",
                "source": "Heritage Foundation",
                "url": "https://example.com/heritage-report",
                "confidence": 0.8,
            },
        ],
    },
    "agreements": [
        "Both sides acknowledge the importance of worker welfare",
        "Both recognize regional economic differences exist",
    ],
    "disagreements": [
        {
            "topic": "Economic Impact",
            "left_position": "Will stimulate economy through increased spending",
            "right_position": "Will harm small businesses and reduce employment",
            "reason": "Different interpretations of economic data and models",
        }
    ],
    "uncertainties": [
        "Long-term effects on automation are unclear",
        "Impact varies significantly by region and industry",
    ],
    "citations": [
        {
            "source": "Economic Policy Institute",
            "url": "https://example.com/epi-study",
            "claim": "Raising minimum wage would lift millions out of poverty",
            "confidence": 0.85,
            "perspective": "left",
        },
        {
            "source": "Center for American Progress",
            "url": "https://example.com/cap-report",
            "claim": "Higher wages lead to increased consumer spending",
            "confidence": 0.8,
            "perspective": "left",
        },
        {
            "source": "UC Berkeley Labor Center",
            "url": "https://example.com/berkeley-study",
            "claim": "Studies show minimal job loss from wage increases",
            "confidence": 0.75,
            "perspective": "left",
        },
        {
            "source": "National Federation of Independent Business",
            "url": "https://example.com/nfib-survey",
            "claim": "Small businesses cannot afford higher wages",
            "confidence": 0.8,
            "perspective": "right",
        },
        {
            "source": "American Enterprise Institute",
            "url": "https://example.com/aei-analysis",
            "claim": "Wage increases lead to automation and job cuts",
            "confidence": 0.75,
            "perspective": "right",
        },
        {
            "source": "Heritage Foundation",
            "url": "https://example.com/heritage-report",
            "claim": "Regional cost of living differences make federal mandate problematic",
            "confidence": 0.8,
            "perspective": "right",
        },
    ],
    "metadata": {"cycles_used": 2, "drafts_synthesized": 3},
}


async def test_evaluators():
    """test all evaluators with mock report"""
    query = "What are perspectives on raising the federal minimum wage to $15?"

    print("\n" + "=" * 60)
    print("TESTING EVALUATORS")
    print("=" * 60)

    import json

    test_case = LLMTestCase(input=query, actual_output=json.dumps(MOCK_REPORT))

    print("\ntesting balance metric...")
    balance_metric = BalanceMetric(threshold=0.5)
    balance_score = balance_metric.measure(test_case)
    print(f"  score: {balance_score:.2f}")
    print(f"  success: {balance_metric.is_successful()}")
    print(f"  reasoning: {balance_metric.reason}")

    print("\ntesting groundedness metric...")
    groundedness_metric = GroundednessMetric(threshold=0.7)
    groundedness_score = groundedness_metric.measure(test_case)
    print(f"  score: {groundedness_score:.2f}")
    print(f"  success: {groundedness_metric.is_successful()}")
    print(f"  reasoning: {groundedness_metric.reason}")

    print("\ntesting citation metric...")
    citation_metric = CitationMetric(threshold=0.8)
    citation_score = citation_metric.measure(test_case)
    print(f"  score: {citation_score:.2f}")
    print(f"  success: {citation_metric.is_successful()}")
    print(f"  reasoning: {citation_metric.reason}")

    print("\n" + "-" * 60)
    avg = (balance_score + groundedness_score + citation_score) / 3
    print(f"average score: {avg:.2f}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_evaluators())
