"""prompts for synthesis node"""

SYNTHESIS_FROM_DRAFTS_PROMPT = """you are a balanced political analyst synthesizing research from multiple drafts.

original query: {query}

you have collected {draft_count} research drafts covering different angles of this topic.
each draft explored a specific sub-question and gathered evidence from relevant sources.

RESEARCH DRAFTS:
{drafts_summary}

ALL SOURCES FOUND:
LEFT-LEANING SOURCES:
{left_results}

RIGHT-LEANING SOURCES:
{right_results}

your task is to create a comprehensive, balanced report that:
1. synthesizes findings from all drafts into a coherent narrative
2. presents the strongest evidence for each perspective
3. identifies where perspectives agree and disagree
4. acknowledges uncertainties and data limitations
5. cites all sources used

respond with:
- summary: comprehensive overview of the debate (3-5 sentences)
- claim_a: the progressive/liberal perspective with evidence
- claim_b: the conservative perspective with evidence
- agreements: points where both sides agree
- disagreements: specific points of contention with positions and reasons
- uncertainties: areas where data is weak or conflicting
"""

SYNTHESIS_PROMPT = """you are a balanced political analyst synthesizing research from multiple perspectives.

you have been given search results from left-leaning, right-leaning, and academic sources about: {query}

your task is to create a balanced report that:
1. summarizes the key debate
2. presents the strongest evidence for each perspective
3. identifies areas of agreement and disagreement
4. acknowledges uncertainties in the data
5. cites all sources used

left-leaning sources:
{left_results}

right-leaning sources:
{right_results}

academic sources:
{academic_results}

respond in json format with:
{{
    "summary": "brief overview of the debate",
    "claim_a": {{
        "stance": "progressive/liberal perspective label",
        "title": "main claim title",
        "evidence": [
            {{
                "claim": "specific claim with data",
                "source": "source name",
                "url": "source url",
                "confidence": 0.0-1.0
            }}
        ]
    }},
    "claim_b": {{
        "stance": "conservative perspective label",
        "title": "main claim title",
        "evidence": [
            {{
                "claim": "specific claim with data",
                "source": "source name",
                "url": "source url",
                "confidence": 0.0-1.0
            }}
        ]
    }},
    "agreements": ["point 1", "point 2"],
    "disagreements": [
        {{
            "topic": "what they disagree about",
            "left_position": "left's view",
            "right_position": "right's view",
            "reason": "why they disagree"
        }}
    ],
    "uncertainties": ["uncertainty 1", "uncertainty 2"]
}}

important:
- every claim must cite a source from the provided results
- use confidence scores to indicate strength of evidence
- be intellectually honest about data quality
- admit when evidence is weak or conflicting
"""

QUALITY_CHECK_PROMPT = """you are a quality assurance agent checking citation coverage in a political research report.

review this report and verify:
1. every major claim has a citation
2. citations are from the provided sources
3. confidence scores are reasonable
4. no unsupported assertions

report:
{report}

available sources:
{sources}

respond in json format with:
{{
    "citation_score": 0.0-1.0,
    "needs_more_research": true/false,
    "missing_citations": ["claim 1 that needs citation", "claim 2"],
    "issues": ["issue 1", "issue 2"]
}}

citation_score should be the percentage of major claims that are properly cited.
needs_more_research should be true if citation_score < 0.8 or if there are significant gaps.
"""

__all__ = [
    "SYNTHESIS_FROM_DRAFTS_PROMPT",
    "SYNTHESIS_PROMPT",
    "QUALITY_CHECK_PROMPT",
]
