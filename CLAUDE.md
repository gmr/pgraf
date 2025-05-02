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
* Python 3.12+ with strict typing
* PEP-8 with 79 character line length
* Single quotes for strings, double quotes for docstrings
* Google-style docstrings with Args/Returns sections
* Import order: stdlib → third-party → local, alphabetized within groups
* Type annotations everywhere, validated with mypy + pydantic plugin
* Exception handling: raise specific exceptions with descriptive messages
* Function naming: snake_case, class naming: CapWords
* Test files must be named test_*.py and use unittest framework
* Database operations use psycopg3 with async pool patterns
* SQL should use proper typing with parameters passed via sql.Identifier/sql.Literal
