# Prompt Abstraction Migration

## Summary

Successfully centralized all prompts from scattered node files into a dedicated `prompts/` directory for easier editing, iteration, and version tracking.

## Changes Made

### 1. Created Prompts Directory Structure

```
prompts/
├── __init__.py              # exports all prompts with version tracking
├── README.md                # documentation
├── models.py                # model configuration per node
├── clarification.py         # clarification node prompts
├── classification.py        # classification node prompts
├── supervisor.py            # supervisor node prompts
├── sub_research.py          # sub_research node prompts
├── synthesis.py             # synthesis node prompts
├── followup.py              # followup node prompts
└── evaluators.py            # evaluation metric prompts
```

### 2. Extracted Prompts

**From `src/agents/nodes/clarification.py`:**
- `CLARIFICATION_PROMPT` → `prompts/clarification.py`

**From `src/agents/nodes/classification.py`:**
- Inline classification prompt → `prompts/classification.py` as `CLASSIFICATION_PROMPT`

**From `src/agents/nodes/supervisor.py`:**
- `SUPERVISOR_INITIAL_PROMPT` → `prompts/supervisor.py`
- `SUPERVISOR_REVIEW_PROMPT` → `prompts/supervisor.py`

**From `src/agents/nodes/sub_research.py`:**
- Inline system prompt → `prompts/sub_research.py` as `SUB_RESEARCH_SYSTEM_PROMPT`
- `DRAFT_SYNTHESIS_PROMPT` → `prompts/sub_research.py`

**From `src/agents/nodes/synthesis.py`:**
- `SYNTHESIS_FROM_DRAFTS_PROMPT` → `prompts/synthesis.py`

**From `src/agents/nodes/followup.py`:**
- Inline system prompt → `prompts/followup.py` as `FOLLOWUP_SYSTEM_PROMPT`
- Inline final prompt → `prompts/followup.py` as `FOLLOWUP_FINAL_PROMPT`

**From `scripts/evaluators.py`:**
- `BALANCE_PROMPT` → `prompts/evaluators.py`
- `GROUNDEDNESS_PROMPT` → `prompts/evaluators.py`
- `CITATION_PROMPT` → `prompts/evaluators.py`

### 3. Updated Imports

**Node files updated:**
- `src/agents/nodes/clarification.py` - now imports from `prompts`
- `src/agents/nodes/classification.py` - now imports from `prompts`
- `src/agents/nodes/supervisor.py` - now imports from `prompts`
- `src/agents/nodes/sub_research.py` - now imports from `prompts`
- `src/agents/nodes/synthesis.py` - now imports from `prompts`
- `src/agents/nodes/followup.py` - now imports from `prompts`

**Script files updated:**
- `scripts/evaluators.py` - now imports from `prompts`

### 4. Removed Old Files

- Deleted `src/agents/prompts.py` (replaced by `prompts/` directory)

### 5. Added Model Configuration

Created `prompts/models.py` with centralized model configuration:

```python
MODELS = {
    "clarification": "openai/gpt-4o-mini",
    "classification": "openai/gpt-4o",
    "supervisor": "openai/gpt-4o",
    "sub_research": "openai/gpt-4o",
    "synthesis": "openai/gpt-4o",
    "followup": "openai/gpt-4o",
    "evaluators": "openai/gpt-4o",
}
```

## Benefits

1. **Easy Editing**: Change prompts without touching node logic
2. **Quick Iteration**: Run `uv run python scripts/evaluate.py` immediately after prompt changes
3. **Version Tracking**: Track prompt versions in `prompts/__init__.py`
4. **Centralized**: All prompts in one place for easy review
5. **Model Flexibility**: Swap models per node for experiments via `prompts/models.py`

## Verification

All changes verified:
- ✅ All prompts import successfully
- ✅ All node files import successfully
- ✅ All evaluator metrics import successfully
- ✅ All existing tests pass (14/14 tests in `test_agents.py`)

## Usage Example

### Before (scattered prompts):

```python
# in src/agents/nodes/synthesis.py
SYNTHESIS_FROM_DRAFTS_PROMPT = """you are a balanced political analyst..."""

async def synthesis_node(state: AgentState) -> dict:
    prompt = SYNTHESIS_FROM_DRAFTS_PROMPT.format(...)
```

### After (centralized prompts):

```python
# in prompts/synthesis.py
SYNTHESIS_FROM_DRAFTS_PROMPT = """you are a balanced political analyst..."""

# in src/agents/nodes/synthesis.py
from prompts import SYNTHESIS_FROM_DRAFTS_PROMPT

async def synthesis_node(state: AgentState) -> dict:
    prompt = SYNTHESIS_FROM_DRAFTS_PROMPT.format(...)
```

## Next Steps

1. Edit prompts in `prompts/` directory as needed
2. Run evaluations after each change: `uv run python scripts/evaluate.py`
3. Compare results in `scripts/results/`
4. Update `PROMPT_VERSION` in `prompts/__init__.py` when making significant changes
5. Commit improved prompts with descriptive messages

## Workflow

```bash
# 1. Edit a prompt
vim prompts/synthesis.py

# 2. Run evaluation to benchmark
uv run python scripts/evaluate.py

# 3. Compare results with previous runs
ls scripts/results/

# 4. If scores improved, commit
git add prompts/
git commit -m "prompt: improve synthesis balance scoring"
```

