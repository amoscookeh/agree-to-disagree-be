"""prompts for classification node"""

CLASSIFICATION_PROMPT = """you are a message classifier for a political research assistant.

given the conversation history and current message, determine if this is:
1. "research_prompt" - a new research question requiring full research workflow
2. "follow_up_question" - a follow-up question about the previous research

conversation history:
{conversation_history}

{report_context}

current message: {query}

guidelines:
- if asking about specific details from the report → follow_up_question
- if asking for clarification or more info on a topic → follow_up_question
- if introducing a completely new topic → research_prompt
- if asking to compare or analyze the report → follow_up_question
- if asking "what about X" where X is related to report → follow_up_question

respond in json format with:
{{
    "message_type": "research_prompt" or "follow_up_question",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation of classification"
}}
"""

QUERY_CLASSIFIER_PROMPT = """you are a query classifier for a US political research tool.

determine if this query is:
1. about US politics (federal, state, or local)
2. a political topic (policy, elections, governance, etc.)
3. appropriate for balanced research

query: {query}

respond in json format with:
{{
    "is_political": true/false,
    "is_us_focused": true/false,
    "is_appropriate": true/false,
    "reason": "brief explanation",
    "suggested_refinement": "how to make it appropriate (if not appropriate)"
}}

examples of appropriate queries:
- "what are perspectives on immigration policy?"
- "how do different sides view the affordable care act?"
- "what's the debate over gun control legislation?"

examples of inappropriate queries:
- "who is the best president?" (subjective, not research-focused)
- "what is brexit?" (not US politics)
- "how do i register to vote?" (not a debate topic)
"""

__all__ = ["CLASSIFICATION_PROMPT", "QUERY_CLASSIFIER_PROMPT"]
