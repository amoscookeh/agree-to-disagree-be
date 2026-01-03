"""custom deepeval metrics for political research evaluation"""

import json

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase
from pydantic import BaseModel, Field

from prompts.evaluators import BALANCE_PROMPT, CITATION_PROMPT, GROUNDEDNESS_PROMPT
from prompts.models import EVALUATOR_MODEL
from src.agents.llm import get_llm


def _parse_report(test_case: LLMTestCase) -> dict | None:
    """parse report from test case, handling both dict and string inputs"""
    actual_output = test_case.actual_output

    if isinstance(actual_output, dict):
        return actual_output

    if isinstance(actual_output, str):
        try:
            return json.loads(actual_output)
        except json.JSONDecodeError:
            return None

    return None


class BalanceScore(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    left_evidence_count: int
    right_evidence_count: int
    reasoning: str


class GroundednessScore(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    grounded_claims: int
    ungrounded_claims: int
    reasoning: str


class CitationScore(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    total_claims: int
    cited_claims: int
    reasoning: str


class BalanceMetric(BaseMetric):
    """measures if both political perspectives are fairly represented"""

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""
        self.success = False

    def measure(self, test_case: LLMTestCase) -> float:
        query = test_case.input
        report = _parse_report(test_case)

        if not report:
            self.score = 0.0
            self.reason = "invalid report format"
            self.success = False
            return self.score

        claim_a = report.get("claim_a", {})
        claim_b = report.get("claim_b", {})

        left_evidence_count = len(claim_a.get("evidence", []))
        right_evidence_count = len(claim_b.get("evidence", []))

        prompt = BALANCE_PROMPT.format(
            query=query,
            summary=report.get("summary", ""),
            left_title=claim_a.get("title", ""),
            left_stance=claim_a.get("stance", ""),
            left_evidence_count=left_evidence_count,
            right_title=claim_b.get("title", ""),
            right_stance=claim_b.get("stance", ""),
            right_evidence_count=right_evidence_count,
            agreements_count=len(report.get("agreements", [])),
            disagreements_count=len(report.get("disagreements", [])),
            uncertainties_count=len(report.get("uncertainties", [])),
        )

        llm = get_llm(EVALUATOR_MODEL)
        structured_llm = llm.with_structured_output(BalanceScore)
        result = structured_llm.invoke(prompt)

        self.score = result.score
        self.reason = result.reasoning
        self.success = self.score >= self.threshold

        return self.score

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self):
        return "Balance"


class GroundednessMetric(BaseMetric):
    """measures if claims are grounded in provided sources"""

    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""
        self.success = False

    def measure(self, test_case: LLMTestCase) -> float:
        query = test_case.input
        report = _parse_report(test_case)

        if not report:
            self.score = 0.0
            self.reason = "invalid report format"
            self.success = False
            return self.score

        claim_a = report.get("claim_a", {})
        claim_b = report.get("claim_b", {})
        citations = report.get("citations", [])

        left_claims = "\n".join(
            f"- {e.get('claim', '')}" for e in claim_a.get("evidence", [])
        )
        right_claims = "\n".join(
            f"- {e.get('claim', '')}" for e in claim_b.get("evidence", [])
        )

        sources = "\n".join(
            f"- {c.get('source', '')}: {c.get('url', '')}" for c in citations
        )

        prompt = GROUNDEDNESS_PROMPT.format(
            query=query,
            summary=report.get("summary", ""),
            left_claims=left_claims,
            right_claims=right_claims,
            sources=sources,
        )

        llm = get_llm(EVALUATOR_MODEL)
        structured_llm = llm.with_structured_output(GroundednessScore)
        result = structured_llm.invoke(prompt)

        self.score = result.score
        self.reason = result.reasoning
        self.success = self.score >= self.threshold

        return self.score

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self):
        return "Groundedness"


class CitationMetric(BaseMetric):
    """measures citation coverage in the report"""

    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""
        self.success = False

    def measure(self, test_case: LLMTestCase) -> float:
        query = test_case.input
        report = _parse_report(test_case)

        if not report:
            self.score = 0.0
            self.reason = "invalid report format"
            self.success = False
            return self.score

        claim_a = report.get("claim_a", {})
        claim_b = report.get("claim_b", {})

        left_evidence = "\n".join(
            f"- {e.get('claim', '')} [source: {e.get('source', 'none')}, url: {e.get('url', 'none')}]"
            for e in claim_a.get("evidence", [])
        )
        right_evidence = "\n".join(
            f"- {e.get('claim', '')} [source: {e.get('source', 'none')}, url: {e.get('url', 'none')}]"
            for e in claim_b.get("evidence", [])
        )

        prompt = CITATION_PROMPT.format(
            query=query,
            summary=report.get("summary", ""),
            left_evidence=left_evidence,
            right_evidence=right_evidence,
        )

        llm = get_llm(EVALUATOR_MODEL)
        structured_llm = llm.with_structured_output(CitationScore)
        result = structured_llm.invoke(prompt)

        self.score = result.score
        self.reason = result.reasoning
        self.success = self.score >= self.threshold

        return self.score

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self):
        return "Citation Coverage"
