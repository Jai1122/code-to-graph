# CodeToGraph Makefile
# Convenient commands for development and deployment

.PHONY: help install install-dev clean test lint format type-check build docker-up docker-down

# Default target
help:
	@echo "CodeToGraph Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install      Install the package and dependencies"
	@echo "  install-dev  Install with development dependencies"
	@echo "  clean        Clean up build artifacts and cache"
	@echo ""
	@echo "Development:"
	@echo "  test         Run tests"
	@echo "  lint         Run linting checks"
	@echo "  format       Format code with black and isort"
	@echo "  type-check   Run type checking with mypy"
	@echo ""
	@echo "Building:"
	@echo "  build        Build distribution packages"
	@echo ""
	@echo "Docker:"
	@echo "  docker-up    Start Docker services"
	@echo "  docker-down  Stop Docker services"
	@echo ""
	@echo "Analysis:"
	@echo "  analyze      Analyze the test repository"
	@echo "  status       Check system status"

# Installation targets
install:
	python3 -m venv .venv --upgrade-deps || python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install -e .

install-dev: install
	.venv/bin/pip install -r dev-requirements.txt

# Clean up
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Development targets
test:
	.venv/bin/pytest tests/ -v --cov=code_to_graph --cov-report=term-missing

lint:
	.venv/bin/flake8 src/ tests/
	.venv/bin/black --check src/ tests/
	.venv/bin/isort --check-only src/ tests/

format:
	.venv/bin/black src/ tests/
	.venv/bin/isort src/ tests/

type-check:
	.venv/bin/mypy src/

# Build targets
build: clean
	.venv/bin/pip install build
	.venv/bin/python -m build

# Docker targets
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# Analysis targets  
analyze:
	@if [ ! -d "test_repo" ]; then echo "Creating test repository..."; mkdir -p test_repo && echo 'package main\nimport "fmt"\nfunc main() { fmt.Println("Hello") }' > test_repo/main.go; fi
	.venv/bin/code-to-graph analyze --repo-path ./test_repo --language go --disable-joern

status:
	.venv/bin/code-to-graph status

# Quick development setup
dev-setup: install-dev docker-up
	@echo "Development environment ready!"
	@echo "Run 'make status' to check system status"