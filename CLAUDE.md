# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project
pgraf turns PostgreSQL into a property graph engine with typed models and vector search capabilities.

## Commands
* Run all tests: `pytest`
* Run a specific test: `pytest tests/test_file.py::TestClass::test_method -v`
* Run linting: `ruff check .`
* Run formatting: `ruff format .`
* Type checking: `mypy pgraf tests`

## Style Guidelines
* Python 3.12+ with strict typing (requires Python 3.12+)
* PEP-8 with 79 character line length (enforced by ruff)
* Single quotes for strings, double quotes for docstrings
* Google-style docstrings with Args/Returns sections
* Import patterns:
  - Import order: stdlib → third-party → local, alphabetized within groups
  - Import modules rather than individual classes or functions
  - Use explicit imports (no star imports)
  - Group imports with blank lines between categories
* Type annotations:
  - Type annotations on all functions, parameters, and return values
  - Use pydantic models for validating complex data structures
  - Use type hints from `typing` module extensively
  - Support for generic types, TypeVar, and Union types
* Exception handling:
  - Raise specific exceptions with descriptive messages
  - Custom exceptions should inherit from standard exceptions
* Naming conventions:
  - Function naming: snake_case
  - Class naming: CapWords
  - Constants: UPPER_CASE
* Testing:
  - Test files must be named test_*.py and use unittest framework
  - Use specific assertions (assertEqual, assertIsInstance, etc.)
* Database operations:
  - Use psycopg3 with async pool patterns
  - Use context managers for database operations
  - SQL should use proper typing with parameters via sql.Identifier/sql.Literal
* Asynchronous patterns:
  - Use async/await for database operations
  - Use contextlib.asynccontextmanager for async context managers
  - Use proper typing with AsyncGenerator and AsyncIterator
