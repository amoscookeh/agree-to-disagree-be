# Agree to Disagree - Backend

AI-powered political research that surfaces progressive and conservative perspectives with citations—helping Americans form informed opinions without echo chambers.

**Frontend Repository:** [agree-to-disagree-fe](https://github.com/amoscookeh/agree-to-disagree-fe)

**The Problem:** Political information is fragmented across biased sources, making it time-consuming and difficult for people to understand multiple perspectives. Most Americans rely on 1-2 sources that fit their existing views or get lost in information overload when trying to research opposing viewpoints. This contributes to polarization and poorly-informed political opinions.

**My Solution:** Ask a political question and receive a balanced report analyzing competing claims, evidence from both sides, and clear explanations of where perspectives agree and disagree—leaving you informed enough to form your own opinion.

## Example

```bash
# start server
./scripts/dev.sh start

# ask a political question
curl -N -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are perspectives on immigration policy?"}'

# returns SSE stream with:
# - clarification (if needed)
# - supervisor generating sub-queries
# - parallel research across left/right sources
# - drafts from each research cycle
# - final balanced report with citations
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

### Multi-Agent System

- **Multi-cycle deep research**: supervisor generates sub-queries, reviews drafts, decides when to synthesize (max 3 cycles)
- **Parallel sub-query execution**: all sub-queries in a cycle run simultaneously for speed
- **Query clarification**: validates US politics scope, asks clarifying questions
- **Follow-up questions**: iterative tool-calling agent with search_left/search_right tools
- **Balanced source coverage**: left-leaning (Guardian, NYT), right-leaning (NY Post, Breitbart, Daily Wire, NewsAPI)

See [agents README](src/agents/README.md) for detailed graph architecture, node descriptions, and PlantUML flow diagram.

### System Features

- **Real-time streaming**: server-sent events for progress updates
- **Conversation memory**: LangGraph checkpointer persists thread history
- **Citation tracking**: every claim linked to source with URL
- **Graceful degradation**: continues on partial data source failures
- **Structured output**: Pydantic validation for all LLM responses
- **LLM-as-judge evaluation**: balance, groundedness, and citation coverage metrics with benchmark dataset

### Integrations

- **OpenRouter**: LLM inference (Grok 4.1 Fast)
- **Supabase**: PostgreSQL database with conversation persistence
- **SerpAPI**: optional Google Search for statistics and additional sources
- **News APIs**: Guardian, NYT, NewsAPI for real-time political coverage
- **RSS Feeds**: NY Post, Breitbart, Daily Wire for conservative perspectives

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

**Defaults:**

- Model: Grok 4.1 Fast (via OpenRouter)
- Temperature: 0.7
- Citation threshold: 80%
- Max research cycles: 3
- Max follow-up tool calls: 10

## Architecture

**Multi-agent workflow:**

1. **Classification** - determines if follow-up or new research
2. **Clarification** - validates US politics query, may ask user for clarification
3. **Supervisor** - generates 2-4 sub-queries (left/right/both angles), reviews drafts after each cycle, decides continue or synthesize
4. **Sub-research** - executes all pending sub-queries in parallel per cycle, searches left/right sources based on angle, generates mini-report draft
5. **Synthesis** - combines all drafts into balanced final report
6. **Follow-up** - handles follow-up questions with iterative tool calling (search_left, search_right, done)

**Key patterns:**

- LangGraph StateGraph with conditional routing
- PostgresSaver checkpointer for conversation memory
- Structured output (Pydantic) for all LLM responses
- Graceful degradation: if one data source fails, continue with others
- Registry pattern for extensible data sources

**Stack:** FastAPI, LangGraph, LangChain, OpenRouter, Supabase, UV

See [agents README](src/agents/README.md) for detailed graph architecture.

## Project Status

**MVP in active development.** API is unstable and may change.

**Supported:**

- Python 3.11+
- macOS/Linux
- US politics queries only
- English language only

**Known limitations:**

- API rate limits: Guardian 500/day, NYT 500/day
- Max 3 research cycles to prevent infinite loops

**Guarantees:**

- Graceful degradation on data source failures
- All claims in report have citations
- Conversation history persisted via LangGraph checkpointer

## Future Plans

**Prompt & Model Optimization:**

- Prompt refinement based on evaluation benchmark scores
- Model comparison and selection (Grok vs GPT-4o vs Claude)
- Token usage tracking and cost optimization per node
- Expanded evaluation datasets (clarification, synthesis quality)

**Enhanced Research Capabilities:**

- Academic sources (Semantic Scholar integration)
- Enhanced SerpAPI tool usage (LLM decides when to search for stats)
- Deep web research with Firecrawl for content extraction
- Multi-country support (starting with UK, Canada)
- Historical policy impact analysis

**Observability & Monitoring:**

- LangSmith integration for distributed tracing
- Per-node token usage and latency tracking
- User-level cost analytics
- Research quality dashboards

**Infrastructure:**

- SSE cancellation fix (decouple research from streaming)
- Background job processing for long research tasks
- Rate limiting per user
- Caching layer for common queries

See [dev-timeline.md](.cursor/docs/dev-timeline.md) for detailed roadmap.

## Contributing

Run tests and linters before committing:

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```
