# Agents Module

LangGraph-based agent workflow for balanced political research.

## Current Implementation Status

| Node                 | Status         | Description                                               |
| -------------------- | -------------- | --------------------------------------------------------- |
| `clarification_node` | ✅ Implemented | Analyzes query clarity, generates clarification questions |
| `research_node`      | ✅ Implemented | Parallel search across left/right data sources            |
| `synthesis_node`     | ⏳ TODO        | Synthesize results into balanced report                   |
| `quality_check_node` | ⏳ TODO        | Verify citation coverage, trigger re-research if needed   |

## Graph Flow

### Current Flow (Implemented)

```plantuml
@startuml current_flow
!theme plain
skinparam backgroundColor #FEFEFE
skinparam defaultFontName Consolas

title Current LangGraph Flow (Implemented)

[*] --> clarification_node : user query

state clarification_node {
    [*] --> analyze_query
    analyze_query --> check_vague : heuristic check
    check_vague --> llm_analysis : not obviously vague
    check_vague --> return_questions : obviously vague
    llm_analysis --> return_refined : clear
    llm_analysis --> return_questions : needs clarification
}

clarification_node --> needs_clarification_check

state needs_clarification_check <<choice>>

needs_clarification_check --> [*] : needs_clarification=true\n(return to user)
needs_clarification_check --> research_node : needs_clarification=false

state research_node {
    [*] --> create_registry
    create_registry --> parallel_search

    state parallel_search {
        [*] --> search_left
        [*] --> search_right
        search_left --> collect_results
        search_right --> collect_results
    }

    parallel_search --> return_results
}

research_node --> [*] : results collected\n(awaiting synthesis)

@enduml
```

### Full Planned Flow

```plantuml
@startuml full_flow
!theme plain
skinparam backgroundColor #FEFEFE

title Full LangGraph Flow

(*) --> "clarification"
if "needs_clarification?" then
  -->[true] "wait for user"
  --> "clarification"
else
  -->[false] "research"
endif

"research" --> "synthesis"
"synthesis" --> "quality_check"

if "needs_more_research?" then
  -->[true, loop < MAX_LOOP] "research"
else
  -->[false] "report"
endif

"report" --> (*)

@enduml
```
