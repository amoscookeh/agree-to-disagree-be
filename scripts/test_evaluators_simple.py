"""simple test for evaluators without pytest"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from deepeval.test_case import LLMTestCase

from scripts.evaluators import BalanceMetric


def test_invalid_report():
    """test with invalid report"""
    print("testing invalid report...")
    test_case = LLMTestCase(input="test query", actual_output="invalid json")

    metric = BalanceMetric(threshold=0.5)
    score = metric.measure(test_case)

    assert score == 0.0, f"expected 0.0, got {score}"
    assert not metric.is_successful(), "should not be successful"
    assert "invalid" in metric.reason.lower(), (
        f"reason should mention invalid: {metric.reason}"
    )
    print("  ✓ invalid report test passed")


def test_valid_report():
    """test with valid report"""
    print("testing valid report...")

    report = {
        "summary": "test summary",
        "claim_a": {
            "stance": "progressive",
            "title": "Left",
            "evidence": [
                {
                    "claim": "claim 1",
                    "source": "source 1",
                    "url": "http://example.com/1",
                    "confidence": 0.8,
                },
                {
                    "claim": "claim 2",
                    "source": "source 2",
                    "url": "http://example.com/2",
                    "confidence": 0.7,
                },
            ],
        },
        "claim_b": {
            "stance": "conservative",
            "title": "Right",
            "evidence": [
                {
                    "claim": "claim 3",
                    "source": "source 3",
                    "url": "http://example.com/3",
                    "confidence": 0.8,
                },
                {
                    "claim": "claim 4",
                    "source": "source 4",
                    "url": "http://example.com/4",
                    "confidence": 0.75,
                },
            ],
        },
        "agreements": ["agreement 1"],
        "disagreements": [
            {
                "topic": "topic 1",
                "left_position": "left",
                "right_position": "right",
                "reason": "reason",
            }
        ],
        "uncertainties": ["uncertainty 1"],
        "citations": [
            {"source": "source 1", "url": "http://example.com/1", "claim": "claim 1"},
            {"source": "source 2", "url": "http://example.com/2", "claim": "claim 2"},
            {"source": "source 3", "url": "http://example.com/3", "claim": "claim 3"},
            {"source": "source 4", "url": "http://example.com/4", "claim": "claim 4"},
        ],
    }

    test_case = LLMTestCase(input="test query", actual_output=json.dumps(report))

    # test balance metric
    balance_metric = BalanceMetric(threshold=0.1)  # low threshold
    balance_score = balance_metric.measure(test_case)
    assert 0.0 <= balance_score <= 1.0, f"score should be 0-1, got {balance_score}"
    assert isinstance(balance_metric.reason, str), "reason should be string"
    assert len(balance_metric.reason) > 0, "reason should not be empty"
    print(f"  ✓ balance metric test passed (score: {balance_score:.2f})")


def main():
    print("\n" + "=" * 60)
    print("SIMPLE EVALUATOR TESTS")
    print("=" * 60 + "\n")

    try:
        test_invalid_report()
        test_valid_report()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60 + "\n")

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}\n")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
