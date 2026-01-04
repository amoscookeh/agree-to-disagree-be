"""classification node prompts"""

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

__all__ = ["CLASSIFICATION_PROMPT"]
