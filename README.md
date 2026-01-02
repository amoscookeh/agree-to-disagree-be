# Agree to Disagree - Backend

Backend API for balanced political research. Searches multiple news sources across the political spectrum, synthesizes perspectives using LLMs, and returns cited reports via streaming API.

## Quick Start

```bash
# start the server
./scripts/dev.sh start

# test a query
curl -N -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are perspectives on immigration policy?"}'
```

API docs: `http://localhost:8000/docs`

## Installation

```bash
cd agree-to-disagree-be
uv sync
cp .env.example .env
# add your API keys to .env
```

**Requirements:** Python 3.11+, UV package manager, OpenRouter API key, Supabase account

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

Copy `scripts/schema.sql` into Supabase SQL Editor (recommended) or run:

```bash
uv run python scripts/test_connections.py
```

## Features

- **Multi-source research**: Searches left/right/academic sources in parallel
- **LLM synthesis**: Generates balanced reports with GPT-4 via OpenRouter
- **Streaming API**: Server-sent events for real-time progress updates
- **Citation tracking**: Every claim linked to source with confidence scores
- **Agent workflow**: LangGraph orchestrates clarification → research → synthesis → quality check

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
- Model: `x-ai/grok-2-1212` (fast, non-reasoning)
- Temperature: 0.7
- Citation threshold: 80% of claims must be cited

## Architecture

### Agent Workflow

1. **Clarification**: Validates query is US politics, refines phrasing
2. **Research**: Parallel search across left/right/academic sources
3. **Synthesis**: LLM generates balanced report with citations
4. **Quality Check**: Validates citation coverage (>80% threshold)

### Data Sources

- **Left**: Guardian, NYT
- **Right**: NY Post, Fox News (via NewsAPI)
- **Academic**: Semantic Scholar, Census (planned)

### Tech Stack

- **FastAPI**: Async web framework
- **LangGraph**: Agent orchestration
- **LangChain**: LLM integration (ChatOpenAI)
- **OpenRouter**: LLM API gateway (Grok, GPT-4, Claude, etc.)
- **Supabase**: PostgreSQL database
- **UV**: Python package manager

## Project Status

**Status:** MVP in development

**Stability:** Experimental - API may change

**Supported:** Python 3.11+, tested on macOS/Linux

**Known limitations:**
- US politics only
- English language only
- Rate limits depend on API keys (Guardian: 500/day, NYT: 500/day)
- No conversation memory yet (planned)

## Contributing

Run tests and linting before submitting:

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```

See `.cursor/docs/tdd.md` for architecture details.
