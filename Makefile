.PHONY: setup install test lint format check pre-commit all

# Set up Poetry environment and install dependencies
setup:
	poetry install
	poetry run pre-commit install

# Install development tools only (alias of setup in poetry context)
install:
	poetry install

# Run tests
test:
	poetry run pytest --cov=. --cov-report=term-missing

# Run linting
lint:
	poetry run flake8 --exclude=.venv

# Auto-format code
format:
	poetry run black .

# Run all checks (formatting, lint, type checking, tests)
check:
	poetry run black --check . && poetry run flake8 --exclude=.venv && poetry run mypy . --explicit-package-bases


# Install pre-commit hooks
pre-commit:
	poetry run pre-commit install

# Run everything
all: format lint test check
