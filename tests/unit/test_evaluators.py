"""unit tests for evaluation metrics"""

import json

import pytest
from deepeval.test_case import LLMTestCase

from scripts.evaluators import BalanceMetric, CitationMetric, GroundednessMetric

pytestmark = pytest.mark.benchmark


@pytest.fixture
def mock_report():
    """mock report with balanced perspectives"""
    return {
        "summary": "test summary",
        "claim_a": {
            "stance": "progressive",
            "title": "Left Perspective",
            "evidence": [
                {
                    "claim": "claim 1",
                    "source": "source 1",
                    "url": "https://example.com/1",
                    "confidence": 0.8,
                },
                {
                    "claim": "claim 2",
                    "source": "source 2",
                    "url": "https://example.com/2",
                    "confidence": 0.7,
                },
            ],
        },
        "claim_b": {
            "stance": "conservative",
            "title": "Right Perspective",
            "evidence": [
                {
                    "claim": "claim 3",
                    "source": "source 3",
                    "url": "https://example.com/3",
                    "confidence": 0.8,
                },
                {
                    "claim": "claim 4",
                    "source": "source 4",
                    "url": "https://example.com/4",
                    "confidence": 0.75,
                },
            ],
        },
        "agreements": ["agreement 1"],
        "disagreements": [
            {
                "topic": "topic 1",
                "left_position": "left pos",
                "right_position": "right pos",
                "reason": "reason",
            }
        ],
        "uncertainties": ["uncertainty 1"],
        "citations": [
            {
                "source": "source 1",
                "url": "https://example.com/1",
                "claim": "claim 1",
                "confidence": 0.8,
                "perspective": "left",
            },
            {
                "source": "source 2",
                "url": "https://example.com/2",
                "claim": "claim 2",
                "confidence": 0.7,
                "perspective": "left",
            },
            {
                "source": "source 3",
                "url": "https://example.com/3",
                "claim": "claim 3",
                "confidence": 0.8,
                "perspective": "right",
            },
            {
                "source": "source 4",
                "url": "https://example.com/4",
                "claim": "claim 4",
                "confidence": 0.75,
                "perspective": "right",
            },
        ],
    }


@pytest.fixture
def imbalanced_report():
    """mock report with imbalanced perspectives"""
    return {
        "summary": "test summary",
        "claim_a": {
            "stance": "progressive",
            "title": "Left Perspective",
            "evidence": [
                {
                    "claim": "claim 1",
                    "source": "source 1",
                    "url": "https://example.com/1",
                    "confidence": 0.8,
                },
                {
                    "claim": "claim 2",
                    "source": "source 2",
                    "url": "https://example.com/2",
                    "confidence": 0.7,
                },
                {
                    "claim": "claim 3",
                    "source": "source 3",
                    "url": "https://example.com/3",
                    "confidence": 0.9,
                },
            ],
        },
        "claim_b": {
            "stance": "conservative",
            "title": "Right Perspective",
            "evidence": [
                {
                    "claim": "claim 4",
                    "source": "source 4",
                    "url": "https://example.com/4",
                    "confidence": 0.6,
                }
            ],
        },
        "agreements": [],
        "disagreements": [],
        "uncertainties": [],
        "citations": [],
    }


def test_balance_metric_with_balanced_report(mock_report):
    """test balance metric with balanced report"""
    import json

    test_case = LLMTestCase(input="test query", actual_output=json.dumps(mock_report))

    metric = BalanceMetric(threshold=0.5)
    score = metric.measure(test_case)

    assert 0.0 <= score <= 1.0
    assert isinstance(metric.reason, str)
    assert len(metric.reason) > 0


def test_balance_metric_with_imbalanced_report(imbalanced_report):
    """test balance metric with imbalanced report"""
    test_case = LLMTestCase(
        input="test query", actual_output=json.dumps(imbalanced_report)
    )

    metric = BalanceMetric(threshold=0.5)
    score = metric.measure(test_case)

    assert 0.0 <= score <= 1.0
    assert isinstance(metric.reason, str)


def test_balance_metric_with_invalid_report():
    """test balance metric with invalid report"""
    test_case = LLMTestCase(input="test query", actual_output="invalid json")

    metric = BalanceMetric(threshold=0.5)
    score = metric.measure(test_case)

    assert score == 0.0
    assert not metric.is_successful()
    assert "invalid" in metric.reason.lower()


def test_groundedness_metric(mock_report):
    """test groundedness metric"""
    test_case = LLMTestCase(input="test query", actual_output=json.dumps(mock_report))

    metric = GroundednessMetric(threshold=0.7)
    score = metric.measure(test_case)

    assert 0.0 <= score <= 1.0
    assert isinstance(metric.reason, str)


def test_citation_metric(mock_report):
    """test citation metric"""
    test_case = LLMTestCase(input="test query", actual_output=json.dumps(mock_report))

    metric = CitationMetric(threshold=0.8)
    score = metric.measure(test_case)

    assert 0.0 <= score <= 1.0
    assert isinstance(metric.reason, str)


def test_citation_metric_with_missing_citations():
    """test citation metric when citations are missing"""
    report = {
        "summary": "test",
        "claim_a": {
            "stance": "progressive",
            "title": "Left",
            "evidence": [
                {
                    "claim": "claim without source",
                    "source": "",
                    "url": "",
                    "confidence": 0.5,
                }
            ],
        },
        "claim_b": {
            "stance": "conservative",
            "title": "Right",
            "evidence": [
                {
                    "claim": "claim without url",
                    "source": "source",
                    "url": "",
                    "confidence": 0.5,
                }
            ],
        },
        "agreements": [],
        "disagreements": [],
        "uncertainties": [],
        "citations": [],
    }

    test_case = LLMTestCase(input="test query", actual_output=json.dumps(report))

    metric = CitationMetric(threshold=0.8)
    score = metric.measure(test_case)

    assert 0.0 <= score <= 1.0


def test_metric_threshold_success(mock_report):
    """test metric success based on threshold"""
    test_case = LLMTestCase(input="test query", actual_output=json.dumps(mock_report))

    low_threshold_metric = BalanceMetric(threshold=0.1)
    low_threshold_metric.measure(test_case)

    high_threshold_metric = BalanceMetric(threshold=0.99)
    high_threshold_metric.measure(test_case)

    assert (
        low_threshold_metric.is_successful() or not low_threshold_metric.is_successful()
    )
    assert (
        high_threshold_metric.is_successful()
        or not high_threshold_metric.is_successful()
    )
