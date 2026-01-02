# Agree to Disagree - Backend

Backend API for the Agree to Disagree political research platform.

## Tech Stack

- **FastAPI**: Modern async web framework
- **LangGraph**: Agent orchestration and workflow management
- **LangChain**: LLM integration and tooling
- **Supabase**: Database and authentication
- **OpenRouter**: LLM API gateway
- **UV**: Fast Python package manager

## Setup

### Prerequisites

- Python 3.11+
- UV package manager
- Supabase account
- OpenRouter API key

### Installation

```bash
# navigate to backend directory
cd agree-to-disagree-be

# install dependencies
uv sync

# create .env file and add your API keys
cp .env.example .env
# edit .env with your actual keys
```

### Environment Variables

See `.env.example` for the template.

## Development

### Quick Start with Dev Script

The `scripts/dev.sh` helper provides common commands:

```bash
# test api connections
./scripts/dev.sh test-connections

# start development server
./scripts/dev.sh start

# run tests
./scripts/dev.sh test

# check code quality
./scripts/dev.sh check-all
```

See all available commands:

```bash
./scripts/dev.sh
```

### Setup Database

Create database tables (see `DATABASE_SETUP.md` for options):

```bash
# Option 1: Use Supabase SQL Editor (recommended)
# Copy scripts/schema.sql into Supabase SQL Editor

# Option 2: Manual connection
uv run python scripts/test_connections.py
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

### Run Tests

```bash
# run all tests
uv run pytest

# run with coverage
uv run pytest --cov=src --cov-report=html

# run specific test file
uv run pytest tests/unit/test_agents.py

# run with verbose output
uv run pytest -v -s
```

### Linting & Formatting

```bash
# run ruff linter
uv run ruff check .

# fix auto-fixable issues
uv run ruff check --fix .

# format code
uv run ruff format .

# type checking
uv run mypy src
```

## Project Structure

```
agree-to-disagree-be/
├── src/
│   ├── api/
│   │   ├── routes/          # api endpoints
│   │   └── schemas.py       # pydantic models for api
│   ├── agents/
│   │   ├── nodes/           # langgraph agent nodes
│   │   ├── graph.py         # agent workflow definition
│   │   └── state.py         # agent state management
│   ├── data_sources/
│   │   ├── left_leaning/    # left-leaning news sources
│   │   ├── right_leaning/   # right-leaning news sources
│   │   ├── academic/        # academic sources
│   │   ├── base.py          # base data source class
│   │   └── registry.py      # data source registry
│   ├── llm/
│   │   ├── client.py        # llm client wrapper
│   │   └── prompts.py       # prompt templates
│   ├── db/
│   │   ├── client.py        # database client
│   │   └── models.py        # database models
│   ├── utils/
│   │   ├── logger.py        # logging setup
│   │   └── validators.py    # input validation
│   ├── config.py            # configuration management
│   └── main.py              # fastapi app entry point
├── tests/
│   ├── unit/                # unit tests
│   ├── integration/         # integration tests
│   └── conftest.py          # pytest fixtures
├── scripts/                 # utility scripts
├── .env                     # environment variables (not in git)
├── pyproject.toml           # project dependencies
└── README.md
```

## API Endpoints

### Health Check

```bash
GET /health
```

Returns API health status.

### Research (Coming Soon)

```bash
POST /api/research
Content-Type: application/json

{
  "query": "What are the different perspectives on climate change policy?"
}
```

Initiates a research workflow and returns a balanced report.

## Architecture

### Agent Workflow

1. **Clarification**: Validates and refines user query
2. **Research**: Gathers data from multiple sources in parallel
3. **Synthesis**: Generates balanced report with LLM
4. **Quality Check**: Validates citations and bias balance

### Data Sources

- **Left-leaning**: Guardian, NYT, Vox, HuffPost
- **Right-leaning**: NY Post, Breitbart, Daily Wire
- **Academic**: Semantic Scholar, Census Bureau
