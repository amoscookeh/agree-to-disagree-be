#!/bin/bash

# development helper script

set -e

case "$1" in
  start)
    echo "starting development server..."
    uv run fastapi dev src/main.py
    ;;
  
  test)
    echo "running tests..."
    uv run pytest -v
    ;;
  
  test-cov)
    echo "running tests with coverage..."
    uv run pytest --cov=src --cov-report=html --cov-report=term
    echo "coverage report generated in htmlcov/index.html"
    ;;
  
  test-connections)
    echo "testing api connections..."
    uv run python scripts/test_connections.py
    ;;
  
  lint)
    echo "running linter..."
    uv run ruff check .
    ;;
  
  lint-fix)
    echo "fixing linting issues..."
    uv run ruff check --fix .
    ;;
  
  format)
    echo "formatting code..."
    uv run ruff format .
    ;;
  
  type-check)
    echo "running type checker..."
    uv run mypy src
    ;;
  
  check-all)
    echo "running all checks..."
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy src
    uv run pytest
    ;;
  
  clean)
    echo "cleaning build artifacts..."
    rm -rf .pytest_cache
    rm -rf .ruff_cache
    rm -rf .mypy_cache
    rm -rf htmlcov
    rm -rf .coverage
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    echo "cleaned"
    ;;
  
  *)
    echo "usage: ./scripts/dev.sh {command}"
    echo ""
    echo "commands:"
    echo "  start            - start development server"
    echo "  test             - run tests"
    echo "  test-cov         - run tests with coverage"
    echo "  test-connections - test api connections"
    echo "  lint             - check code quality"
    echo "  lint-fix         - fix linting issues"
    echo "  format           - format code"
    echo "  type-check       - run type checker"
    echo "  check-all        - run all checks"
    echo "  clean            - clean build artifacts"
    exit 1
    ;;
esac
