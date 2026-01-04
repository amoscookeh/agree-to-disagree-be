"""synthesis node prompts"""

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

__all__ = ["SYNTHESIS_FROM_DRAFTS_PROMPT"]
