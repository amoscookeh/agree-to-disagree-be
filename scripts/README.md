# Evaluation Scripts

llm-as-judge evaluation framework for measuring research quality using deepeval.

## Overview

this directory contains scripts for evaluating the quality of political research reports using three custom metrics:

1. **balance metric** - measures if both political perspectives are fairly represented
2. **groundedness metric** - verifies claims are grounded in provided sources
3. **citation metric** - evaluates citation coverage for factual claims

## Files

- `evaluate.py` - main evaluation script that runs test queries through the research graph
- `evaluators.py` - custom deepeval metrics implementation
- `test_evaluators.py` - quick test script for validating evaluators with mock data
- `results/` - directory where evaluation results are saved

## Usage

### Quick Test (Mock Data)

test evaluators without running full research:

```bash
cd agree-to-disagree-be
uv run python scripts/test_evaluators.py
```

### Full Evaluation

run complete evaluation on test queries:

```bash
cd agree-to-disagree-be
uv run python scripts/evaluate.py
```

this will:
1. run 5 test queries through the research graph
2. evaluate each report using all three metrics
3. print results to console
4. save detailed results to `results/eval_results_TIMESTAMP.json`

### Custom Queries

edit `TEST_QUERIES` in `evaluate.py` to test different queries:

```python
TEST_QUERIES = [
    "Your custom query here",
    "Another query",
]
```

## Metrics

### Balance Metric

**threshold:** 0.5 (50%)

evaluates if both political perspectives are fairly represented:
- 1.0 = both perspectives thoroughly represented with equal depth
- 0.7 = both present but one slightly more detailed
- 0.5 = noticeable imbalance but both views exist
- 0.3 = heavy bias toward one side
- 0.0 = only one perspective shown

### Groundedness Metric

**threshold:** 0.7 (70%)

checks if claims are grounded in provided sources:
- score = grounded_claims / total_claims
- identifies hallucinated or unsupported claims
- verifies each claim can be traced to sources

### Citation Metric

**threshold:** 0.8 (80%)

measures citation coverage:
- score = cited_claims / total_claims
- ensures factual claims have proper citations
- checks for source name and url presence

## Output Format

### Console Output

```
==============================================================
EVALUATION RESULTS
==============================================================

query: What are perspectives on raising the federal minimum...
  balance:      0.85 ✓
  groundedness: 0.92 ✓
  citation:     0.88 ✓
  average:      0.88

--------------------------------------------------------------
OVERALL AVERAGES:
  balance:      0.82
  groundedness: 0.87
  citation:     0.85
  TOTAL:        0.85
```

### JSON Output

saved to `results/eval_results_TIMESTAMP.json`:

```json
[
  {
    "query": "What are perspectives on raising the federal minimum wage to $15?",
    "scores": {
      "balance": {
        "score": 0.85,
        "reasoning": "Both perspectives well represented...",
        "success": true
      },
      "groundedness": {
        "score": 0.92,
        "reasoning": "All claims traced to sources...",
        "success": true
      },
      "citation": {
        "score": 0.88,
        "reasoning": "Most claims properly cited...",
        "success": true
      },
      "average": 0.88
    },
    "report_metadata": {
      "citations_count": 12,
      "agreements_count": 3,
      "disagreements_count": 4,
      "uncertainties_count": 2,
      "cycles_used": 2
    },
    "timestamp": "2025-01-03T10:30:00Z"
  }
]
```

## GitHub Actions Integration

evaluation runs automatically on:
- pushes to main that modify agent or llm code
- manual trigger via workflow_dispatch

results are uploaded as artifacts and can be viewed in the actions tab.

for pull requests, results are automatically commented on the pr.

## Customization

### Adjust Thresholds

modify thresholds in `evaluate.py`:

```python
metrics = [
    BalanceMetric(threshold=0.6),        # stricter balance requirement
    GroundednessMetric(threshold=0.8),   # stricter groundedness
    CitationMetric(threshold=0.9),       # stricter citation coverage
]
```

### Add New Metrics

create new metric in `evaluators.py`:

```python
from deepeval.metrics import BaseMetric

class YourMetric(BaseMetric):
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""
        self.success = False
    
    def measure(self, test_case: LLMTestCase) -> float:
        # implement your evaluation logic
        return self.score
    
    def is_successful(self) -> bool:
        return self.success
    
    @property
    def __name__(self):
        return "Your Metric Name"
```

## Troubleshooting

### "No report generated"

- check if data sources are accessible
- verify api keys are set in environment
- check logs for errors during research

### "Invalid report format"

- ensure report structure matches expected format
- check synthesis node is returning proper dict

### Low Scores

- review llm prompts in agent nodes
- check if data sources are returning quality results
- verify citation extraction logic in synthesis node

## Dependencies

- `deepeval>=1.6.0` - llm-as-judge framework
- `langchain` - llm integration
- `langgraph` - agent workflow

install with:

```bash
uv sync --dev
```

