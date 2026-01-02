# Agents Module

LangGraph-based agent workflow for balanced political research.

## Nodes

| Node                 | Status         | Description                                               |
| -------------------- | -------------- | --------------------------------------------------------- |
| `clarification_node` | ✅ Implemented | Analyzes query clarity, generates clarification questions |
| `research_node`      | ✅ Implemented | Parallel search across left/right data sources            |
| `synthesis_node`     | ✅ Implemented | Synthesize results into balanced report                   |
| `quality_check_node` | ⏳ TODO        | Verify citation coverage, trigger re-research if needed   |

## Graph Flow

```
                    ┌─────────────────┐
                    │  clarification  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ needs_clarify?  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼ yes                         ▼ no
         ┌────────┐                ┌────────────────┐
         │  END   │                │    research    │
         │(return │                │ (parallel L/R) │
         │ to UI) │                └────────┬───────┘
         └────────┘                         │
                                   ┌────────▼───────┐
                                   │   synthesis    │
                                   │ (LLM report)   │
                                   └────────┬───────┘
                                            │
                                       ┌────▼────┐
                                       │   END   │
                                       └─────────┘
```

## Usage

```python
from src.agents import research_graph

state = {"query": "What are perspectives on immigration?"}
result = await research_graph.ainvoke(state)

# streaming
async for chunk in research_graph.astream(state, stream_mode="custom"):
    print(chunk)
```
