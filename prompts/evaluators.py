"""evaluator prompts for deepeval metrics"""

BALANCE_PROMPT = """evaluate if this political research report fairly represents both perspectives.

query: {query}

report summary: {summary}

left perspective (claim_a):
title: {left_title}
stance: {left_stance}
evidence count: {left_evidence_count}

right perspective (claim_b):
title: {right_title}
stance: {right_stance}
evidence count: {right_evidence_count}

agreements: {agreements_count} points
disagreements: {disagreements_count} points
uncertainties: {uncertainties_count} points

score from 0-1:
- 1.0 = both perspectives thoroughly represented with equal depth
- 0.7 = both present but one slightly more detailed
- 0.5 = noticeable imbalance but both views exist
- 0.3 = heavy bias toward one side
- 0.0 = only one perspective shown

count the evidence items for each side and explain your reasoning."""

GROUNDEDNESS_PROMPT = """check if claims in this report are grounded in the provided sources.

query: {query}

report summary: {summary}

left perspective claims:
{left_claims}

right perspective claims:
{right_claims}

available sources:
{sources}

for each claim in the report, verify it can be traced to the sources.
score 0-1 based on % of claims that are grounded.
list any ungrounded/hallucinated claims."""

CITATION_PROMPT = """evaluate citation coverage in this research report.

query: {query}

report summary: {summary}

left perspective evidence:
{left_evidence}

right perspective evidence:
{right_evidence}

count:
1. total factual claims made
2. claims with proper citations (source + url)

score = cited_claims / total_claims
note any claims that should have citations but don't."""

__all__ = ["BALANCE_PROMPT", "GROUNDEDNESS_PROMPT", "CITATION_PROMPT"]
