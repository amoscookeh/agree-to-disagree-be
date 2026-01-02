# Agree to Disagree - Backend

Backend API for balanced political research. Searches news sources across the political spectrum and returns cited reports via streaming.

## Example

```bash
./scripts/dev.sh start

curl -N -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are perspectives on immigration policy?"}'
```

API docs: http://localhost:8000/docs

## Quick Start

```bash
uv sync
cp .env.example .env  # add API keys
./scripts/dev.sh start
```

## Installation

**Requirements:** Python 3.11+, UV, OpenRouter API key, Supabase account

```bash
uv sync
cp .env.example .env  # add API keys
```

## Usage

### Development Server

```bash
./scripts/dev.sh start              # start server
./scripts/dev.sh test               # run tests
./scripts/dev.sh test-connections   # verify API keys
./scripts/dev.sh check-all          # lint + type check
```

### Testing

```bash
uv run pytest                       # all tests
uv run pytest --cov=src            # with coverage
uv run pytest tests/unit/test_llm.py -v  # specific file
```

### Database Setup

Copy `scripts/schema.sql` into Supabase SQL Editor or run `uv run python scripts/test_connections.py`

## Features

- Multi-source research (left/right/academic sources in parallel)
- LLM synthesis (balanced reports via OpenRouter)
- Streaming API (SSE for real-time progress)
- Citation tracking (every claim linked to source)
- Agent workflow (LangGraph orchestrates clarification → research → synthesis → quality check)

## Configuration

Environment variables (see `.env.example`):

```bash
OPENROUTER_API_KEY=sk-or-xxx        # required
SUPABASE_URL=https://xxx.supabase.co  # required
SUPABASE_KEY=xxx                     # required
GUARDIAN_API_KEY=xxx                 # optional
NYT_API_KEY=xxx                      # optional
NEWSAPI_KEY=xxx                      # optional
```

**Defaults:**

- Model: `x-ai/grok-4.1-fast`
- Temperature: 0.7
- Citation threshold: 80%

## Architecture

**Agent Workflow:**

1. Clarification → validates query is US politics, refines phrasing
2. Research → parallel search across sources
3. Synthesis → generates balanced report with citations
4. Quality Check → validates citation coverage

**Data Sources:**

- Left: Guardian, NYT
- Right: NY Post, Fox News
- Academic: Semantic Scholar, Census (planned)

**Tech Stack:**

- FastAPI (async web framework)
- LangGraph (agent orchestration)
- LangChain (LLM integration)
- OpenRouter (LLM gateway)
- Supabase (PostgreSQL)
- UV (package manager)

## Project Status

MVP in development. API may change.

**Supported:** Python 3.11+, macOS/Linux

**Limitations:**

- US politics only
- English only
- Rate limits: Guardian (500/day), NYT (500/day)
- No conversation memory

## Contributing

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```

See `.cursor/docs/tdd.md` for details.
