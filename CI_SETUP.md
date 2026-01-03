# CI Setup

## Overview

The backend has two separate CI jobs:

1. **Tests** - Fast unit tests and non-API integration tests (runs on every push/PR)
2. **Benchmarking** - DeepEval LLM quality tests (runs only on main branch pushes)

## Test Job

Runs on every push and PR. Skips tests that require external API keys.

**What it runs:**
- Linting (ruff)
- Type checking (mypy)
- Unit tests
- Integration tests that don't need API keys (RSS feeds, etc.)

**What it skips:**
- Tests marked with `@pytest.mark.requires_api` (Guardian, NYT, NewsAPI)
- Tests marked with `@pytest.mark.benchmark` (DeepEval evaluators)

**Command:**
```bash
pytest -m "not requires_api and not benchmark" -v
```

## Benchmarking Job

Runs only on pushes to main branch. Makes real LLM API calls to evaluate research quality.

**What it runs:**
- All tests marked with `@pytest.mark.benchmark`
- Currently: 7 DeepEval evaluator tests

**Requirements:**
- `OPENROUTER_API_KEY` secret must be set in GitHub Actions

**Command:**
```bash
pytest -m benchmark -v
```

**Cost:** ~$0.10-0.50 per run (depending on LLM usage)

## Running Tests Locally

### Fast tests (no API calls):
```bash
pytest -m "not requires_api and not benchmark" -v
```

### With API keys (integration tests):
```bash
pytest -m "not benchmark" -v
```

### Benchmark tests only:
```bash
pytest -m benchmark -v
```

### All tests:
```bash
pytest -v
```

## Adding New Tests

### Mark API-dependent tests:
```python
@pytest.mark.requires_api
async def test_my_api_integration():
    ...
```

### Mark benchmark tests:
```python
@pytest.mark.benchmark
async def test_my_llm_evaluation():
    ...
```

## GitHub Secrets Required

- `OPENROUTER_API_KEY` - for benchmarking job
- `SUPABASE_URL` - optional, for full integration tests
- `SUPABASE_KEY` - optional, for full integration tests
- `GUARDIAN_API_KEY` - optional, for Guardian integration tests
- `NYT_API_KEY` - optional, for NYT integration tests
- `NEWSAPI_KEY` - optional, for NewsAPI integration tests

