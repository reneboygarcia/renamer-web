## Core Variables
PYTHON := python3
VENV := venv
PIP := $(VENV)/bin/pip
PYTHON_VENV := $(VENV)/bin/python
PROJECT := src/app.py

## Development Dependencies
DEV_PACKAGES := black pylint pytest

# ===========================================
# Core Commands
# ===========================================

.DEFAULT_GOAL := help

.PHONY: help
help: ## Display available commands with descriptions
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available Commands:'
	@awk '/^[a-zA-Z\-\_0-9]+:/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			printf "  %-20s %s\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)

.PHONY: install
install: verify-python ## Install project dependencies
	@echo "Setting up project environment..."
	@$(PYTHON) -m venv $(VENV)
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt
	@echo "\033[0;32m✓ Environment ready! Activate with: source venv/bin/activate\033[0m"

.PHONY: run
run: verify-env ## Launch the TV Show Renamer application
	@echo "Starting application..."
	@$(PYTHON_VENV) -m streamlit run $(PROJECT)

# ===========================================
# Development Commands
# ===========================================

.PHONY: dev-setup
dev-setup: install install-dev-tools setup-env ## Configure complete development environment
	@echo "✓ Development environment configured"

.PHONY: install-dev-tools
install-dev-tools: ## Install development tools
	@echo "Installing development dependencies..."
	@$(PIP) install $(DEV_PACKAGES)

.PHONY: lint
lint: ## Run code quality checks
	@echo "Running code quality checks..."
	@$(VENV)/bin/black .
	@$(VENV)/bin/pylint src tests

.PHONY: test
test: ## Execute test suite
	@echo "Running tests..."
	@$(PYTHON_VENV) -m pytest tests/

# ===========================================
# Environment Management
# ===========================================

.PHONY: setup-env
setup-env: ## Initialize environment configuration
	@if [ ! -f .env ]; then \
		echo "Creating .env file..."; \
		cp .env.example .env; \
		echo "⚠️ Update .env with your TMDb API key"; \
	else \
		echo "✓ .env file exists"; \
	fi

.PHONY: clean
clean: ## Remove all generated files and virtual environment
	@echo "Cleaning project..."
	@rm -rf $(VENV) __pycache__ .pytest_cache .coverage htmlcov build dist *.egg-info
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@echo "✓ Project cleaned"

# ===========================================
# Verification Helpers
# ===========================================

.PHONY: verify-python
verify-python:
	@which python3 > /dev/null || (echo "❌ Python 3 not found" && exit 1)

.PHONY: verify-env
verify-env:
	@test -f .env || (echo "❌ .env file missing. Run 'make setup-env' first" && exit 1)

# ===========================================
# OS-specific configuration
# ===========================================

ifeq ($(OS),Windows_NT)
    PYTHON := python
    VENV := venv
    PIP := $(VENV)\Scripts\pip
    PYTHON_VENV := $(VENV)\Scripts\python
else
    PYTHON := python3
    VENV := venv
    PIP := $(VENV)/bin/pip
    PYTHON_VENV := $(VENV)/bin/python
endif