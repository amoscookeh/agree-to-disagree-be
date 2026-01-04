"""
centralized prompts for the research agent system

edit prompts here and run `uv run python scripts/evaluate.py` to benchmark changes.

version tracking:
- increment when making changes:
  - 1.0.x: minor wording changes
  - 1.x.0: structural changes to prompts
  - x.0.0: major prompt strategy changes
"""

PROMPT_VERSION = "1.0.0"

from prompts.clarification import *
from prompts.classification import *
from prompts.evaluators import *
from prompts.followup import *
from prompts.sub_research import *
from prompts.supervisor import *
from prompts.synthesis import *

__all__ = [
    "PROMPT_VERSION",
    # clarification
    "CLARIFICATION_PROMPT",
    # classification
    "CLASSIFICATION_PROMPT",
    # supervisor
    "SUPERVISOR_INITIAL_PROMPT",
    "SUPERVISOR_REVIEW_PROMPT",
    # sub_research
    "SUB_RESEARCH_SYSTEM_PROMPT",
    "DRAFT_SYNTHESIS_PROMPT",
    # synthesis
    "SYNTHESIS_FROM_DRAFTS_PROMPT",
    # followup
    "FOLLOWUP_SYSTEM_PROMPT",
    "FOLLOWUP_FINAL_PROMPT",
    # evaluators
    "BALANCE_PROMPT",
    "GROUNDEDNESS_PROMPT",
    "CITATION_PROMPT",
]
