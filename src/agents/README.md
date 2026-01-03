# Agents Module

LangGraph-based agent workflow for balanced political research.

## Nodes

| Node                  | Status      | Description                                               |
| --------------------- | ----------- | --------------------------------------------------------- |
| `classification_node` | Implemented | Classifies message as research prompt or follow-up        |
| `clarification_node`  | Implemented | Analyzes query clarity, generates clarification questions |
| `research_node`       | Implemented | Parallel search across left/right data sources            |
| `synthesis_node`      | Implemented | Synthesize results into balanced report                   |
| `followup_node`       | Implemented | Answers follow-up questions with search tools (max 10)    |
| `quality_check_node`  | TODO        | Verify citation coverage, trigger re-research if needed   |

## Graph Flow

```
                    ┌──────────────────┐
                    │ classification   │
                    │ (first msg or    │
                    │  LLM classify)   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ message_type?    │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼ research_prompt             ▼ follow_up_question
    ┌─────────────────┐           ┌─────────────────┐
    │  clarification  │           │    followup     │
    └────────┬────────┘           │ (search tools,  │
             │                    │  max 10 calls)  │
    ┌────────▼────────┐           └────────┬────────┘
    │ needs_clarify?  │                    │
    └────────┬────────┘                    │
             │                             │
      ┌──────┴──────┐                     │
      │             │                     │
      ▼ yes         ▼ no                  │
   ┌──────┐   ┌──────────┐               │
   │ END  │   │ research │               │
   │(wait │   │(parallel │               │
   │ user)│   │   L/R)   │               │
   └──────┘   └────┬─────┘               │
                   │                     │
           ┌───────▼──────┐              │
           │  synthesis   │              │
           │ (LLM report) │              │
           └───────┬──────┘              │
                   │                     │
                   └──────┬──────────────┘
                          │
                     ┌────▼────┐
                     │   END   │
                     └─────────┘
```
