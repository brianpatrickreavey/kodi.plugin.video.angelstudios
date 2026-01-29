# Makefile for auth0-ciam-client package development
SHELL := /bin/bash

.PHONY: test lint format build install clean help

# Default target
help:
	@echo "Available targets:"
	@echo "  test      - Run tests with coverage"
	@echo "  lint      - Run linting (black, flake8, pyright)"
	@echo "  format    - Format code with black"
	@echo "  build     - Build package distribution"
	@echo "  install   - Install package in development mode"
	@echo "  clean     - Clean build artifacts"
	@echo "  help      - Show this help message"

# Testing
test:
	source ../.venv/bin/activate && pytest tests/ -v --cov=auth0_ciam_client --cov-report=term-missing

# Linting and formatting
lint:
	source ../.venv/bin/activate && black --check . --line-length=120
	source ../.venv/bin/activate && flake8 . --max-line-length=120
	source ../.venv/bin/activate && pyright .

format:
	source ../.venv/bin/activate && black . --line-length=120

# Package management
build:
	source ../.venv/bin/activate && python setup.py sdist bdist_wheel

install:
	source ../.venv/bin/activate && pip install -e .

# Cleanup
clean:
	rm -rf dist/ build/ *.egg-info/
	rm -rf .pytest_cache/ .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true