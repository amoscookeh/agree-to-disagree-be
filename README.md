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
uv run pytest -m benchmark -v           # run LLM evaluation benchmarks
```

## Features

- Multi-source research across left/right outlets
- Supervisor-driven deep research with sub-queries
- LLM synthesis via OpenRouter (Grok 4.1)
- Server-sent events for real-time progress
- Citation tracking with source attribution
- Conversation memory via LangGraph checkpointer
- Follow-up questions on existing research
- Optional Google Search via SerpAPI for statistics and additional sources

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
SERPAPI_KEY=xxx  # enables Google Search for statistics
```

**Defaults:** Grok 4.1 Fast, temperature 0.7, 80% citation threshold

## Architecture

**Agent workflow:**
1. Classification - determines if follow-up or new research
2. Clarification - validates US politics query
3. Supervisor - generates sub-queries, manages research cycles (max 3)
4. Sub-research - executes all sub-queries in parallel per cycle
5. Synthesis - combines drafts into balanced report

**Data sources:**
- Left: Guardian, NYT
- Right: NY Post, Breitbart, Daily Wire, NewsAPI
- Academic: Semantic Scholar (planned)

**Stack:** FastAPI, LangGraph, LangChain, OpenRouter, Supabase, UV

## Project Status

MVP in active development. API is unstable.

**Supported:** Python 3.11+, macOS/Linux

**Limitations:** 
- US politics queries only
- English language only
- API rate limits: Guardian 500/day, NYT 500/day

## Contributing

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```
