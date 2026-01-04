"""
sub_research node prompts

variables for SUB_RESEARCH_SYSTEM_PROMPT:
- {sq_query}: the sub-query text
- {sq_angle}: the angle (left, right, or both)
- {angle_desc}: human-readable description of the angle

variables for DRAFT_SYNTHESIS_PROMPT:
- {sub_query}: the sub-query text
- {angle}: the angle (left, right, or both)
- {sources_section}: formatted sources (left, right, google results)
"""

SUB_RESEARCH_SYSTEM_PROMPT = """you are researching a specific aspect of a political topic.

sub-query: {sq_query}
angle: {sq_angle} (focus on {angle_desc})

you have these tools:
- search_news_sources: search left/right-leaning news for articles
- search_google: search google for stats, studies, or additional sources

strategy:
1. first search news sources for the relevant perspective
2. if news sources lack specific statistics or numbers, use google search
3. if news sources return few results (<3), supplement with google search
4. compile findings into a summary

focus on finding concrete evidence and citations."""

DRAFT_SYNTHESIS_PROMPT = """you are synthesizing research results for a specific sub-query.

sub-query: {sub_query}
angle: {angle}

{sources_section}

create a brief synthesis covering:
1. main findings from the sources
2. key points relevant to the sub-query
3. any notable perspectives or disagreements found

respond with:
- summary: a 2-3 sentence synthesis of findings
- key_findings: 2-4 bullet points of important findings
- left_perspective: (if applicable) what left-leaning sources emphasized
- right_perspective: (if applicable) what right-leaning sources emphasized
"""

__all__ = ["SUB_RESEARCH_SYSTEM_PROMPT", "DRAFT_SYNTHESIS_PROMPT"]
