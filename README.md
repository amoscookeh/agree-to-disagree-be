# Agree to Disagree - Backend

Backend API for balanced political research across the spectrum.

## Quick Start

```bash
# start server
./scripts/dev.sh start

# make a research request
curl -N -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are perspectives on immigration policy?"}'

# returns SSE stream with progress events and final report
```

Interactive API docs: http://localhost:8000/docs

## Installation

**Requirements:** Python 3.11+, [UV](https://docs.astral.sh/uv/)

```bash
uv sync
cp .env.example .env
# edit .env with your API keys (OpenRouter, Supabase required)
```

Setup database by running `scripts/schema.sql` in Supabase SQL Editor.

## Usage

```bash
./scripts/dev.sh start              # start server
./scripts/dev.sh test               # run tests
./scripts/dev.sh test-connections   # verify API keys
./scripts/dev.sh check-all          # lint + type check
```

Run specific tests:
```bash
uv run pytest tests/unit/test_llm.py -v
uv run pytest --cov=src
```

## Features

- Multi-source research across left/right/academic outlets
- LLM synthesis via OpenRouter (Grok 4.1)
- Server-sent events for real-time progress
- Citation tracking (80% minimum threshold)
- Conversation memory via LangGraph checkpointer
- Agent workflow: clarification → research → synthesis → quality check

## Configuration

Required environment variables:
```bash
OPENROUTER_API_KEY=sk-or-xxx
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=xxx
```

Optional (improves coverage):
```bash
GUARDIAN_API_KEY=xxx
NYT_API_KEY=xxx
NEWSAPI_KEY=xxx
```

Defaults: Grok 4.1 Fast, temp 0.7, 80% citation threshold

## Architecture

**Agent workflow:**
1. Clarification - validates US politics query
2. Research - parallel search (left/right/academic)
3. Synthesis - generates balanced report
4. Quality Check - validates citations

**Data sources:**
- Left: Guardian, NYT
- Right: NY Post, Breitbart, Daily Wire, NewsAPI
- Academic: Semantic Scholar (planned)

**Stack:** FastAPI, LangGraph, LangChain, OpenRouter, Supabase, UV

## Project Status

MVP in active development. API is unstable.

**Supported:** Python 3.11+, macOS/Linux  
**Limitations:** US politics only, English only, rate limits apply (Guardian 500/day, NYT 500/day)

## Contributing

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```
