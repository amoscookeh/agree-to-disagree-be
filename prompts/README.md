# Prompts Directory

Centralized prompt templates for the research agent system.

## Structure

```
prompts/
├── __init__.py              # exports all prompts with version tracking
├── models.py                # model configuration per node
├── clarification.py         # clarification node prompts
├── classification.py        # classification node prompts
├── supervisor.py            # supervisor node prompts
├── sub_research.py          # sub_research node prompts
├── synthesis.py             # synthesis node prompts
├── followup.py              # followup node prompts
└── evaluators.py            # evaluation metric prompts
```

## Usage

### Importing Prompts

```python
from prompts import CLARIFICATION_PROMPT, SUPERVISOR_INITIAL_PROMPT

# use in your code
prompt = CLARIFICATION_PROMPT.format(query=user_query)
```

### Importing Models

```python
from prompts.models import get_model
from src.agents.llm import get_llm

# get model for a specific node and create llm instance
llm = get_llm(model=get_model("synthesis"))  # uses x-ai/grok-4.1-fast
```

**Model configuration is now integrated into all nodes!** Each node automatically uses the model specified in `prompts/models.py`.

## Workflow for Prompt Changes

1. **Edit a prompt** in the relevant file (e.g., `prompts/synthesis.py`)
2. **Update version** in `prompts/__init__.py` if needed:
   - `1.0.x`: minor wording changes
   - `1.x.0`: structural changes to prompts
   - `x.0.0`: major prompt strategy changes
3. **Run evaluation** to benchmark changes:
   ```bash
   uv run python scripts/evaluate.py
   ```
4. **Compare results** with previous runs:
   ```bash
   ls scripts/results/
   ```
5. **Commit if improved**:
   ```bash
   git add prompts/
   git commit -m "prompt: improve synthesis balance scoring"
   ```

## Prompt Variables

Each prompt file documents the variables it expects. For example:

```python
# prompts/synthesis.py
"""
variables:
- {query}: the refined query
- {draft_count}: number of drafts collected
- {drafts_summary}: formatted summary of all drafts
"""
```

## Model Configuration

Edit `prompts/models.py` to change which model is used for each node:

```python
MODELS = {
    "clarification": "x-ai/grok-4.1-fast",
    "classification": "x-ai/grok-4.1-fast",
    "supervisor": "x-ai/grok-4.1-fast",
    "sub_research": "x-ai/grok-4.1-fast",
    "sub_research_tools": "x-ai/grok-4.1-fast",
    "synthesis": "x-ai/grok-4.1-fast",
    "followup": "x-ai/grok-4.1-fast",
    "evaluators": "x-ai/grok-4.1-fast",
}
```

This makes it easy to experiment with different models per node without touching the node logic.

**Currently using Grok 4.1 Fast** as the default for all nodes (fast, cost-effective). You can upgrade specific nodes to `x-ai/grok-beta` for better reasoning if needed.

## Benefits

1. **Easy editing**: Change prompts without touching node logic
2. **Quick iteration**: Run evals immediately after prompt changes
3. **Version tracking**: Track prompt versions and their impact
4. **Centralized**: All prompts in one place for easy review
5. **Model flexibility**: Swap models per node for experiments

