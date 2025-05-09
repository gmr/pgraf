# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project
pgraf turns PostgreSQL into a lightning fast property graph engine with vector search capabilities, designed for use in AI agents and applications. It combines the reliability of PostgreSQL with vector embeddings and graph capabilities.

### Key Features
- **Property Graph Model**: Nodes and edges with labels and properties
- **Vector Embeddings**: Built-in semantic search using sentence transformers
- **Pydantic Models**: Strong typing with validation for all graph components
- **Asynchronous API**: Modern async/await interfaces for high-performance operations
- **SQL Safety**: Uses psycopg3 with SQL composition to prevent injection attacks

## Project Structure
- `pgraf/` - Core module
  - `embeddings.py` - Vector embedding generation with sentence transformers
  - `errors.py` - Custom exception classes
  - `graph.py` - Main PGraf class for graph operations
  - `models.py` - Pydantic models for nodes, edges, and embeddings
  - `postgres.py` - PostgreSQL connection and query management
  - `queries.py` - SQL query templates and utilities
  - `utils.py` - Helper functions and utilities
- `schema/` - Database schema definitions
  - `pgraf.sql` - PostgreSQL schema with tables, indexes, and stored procedures
- `tests/` - Test suite
- `docs/` - Documentation (MkDocs-based)

## Commands
* Run all tests: `pytest`
* Run a specific test: `pytest tests/test_file.py::TestClass::test_method -v`
* Run linting: `ruff check .`
* Run formatting: `ruff format .`
* Type checking: `mypy pgraf tests`
* Build docs: `python -m mkdocs build`
* Serve docs locally: `python -m mkdocs serve`
* Deploy docs: `hatch run github-pages`

## Core Components

### PGraf Class
The main entry point for all graph operations (`graph.py`), providing methods for:
- Adding/updating/deleting nodes and edges
- Traversing the graph with filtering
- Semantic search with embeddings
- Property and label queries

### Models
Pydantic models (`models.py`) for data validation:
- `Node`: Graph nodes with properties, labels, content, and mimetype
- `Edge`: Relationships between nodes with properties and labels
- `Embedding`: Vector representations of text for semantic search
- `SearchResult`: Enhanced node with similarity score

### Database Schema
PostgreSQL schema (`schema/pgraf.sql`) with:
- `nodes` table: Stores graph nodes with properties, content, and vector index
- `edges` table: Stores relationships between nodes
- `embeddings` table: Stores vector embeddings for semantic search
- Stored procedures for key operations
- Indexes for optimized queries

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
  - Use YAML fixtures for test data when appropriate
* Database operations:
  - Use psycopg3 with async pool patterns
  - Use context managers for database operations
  - SQL should use proper typing with parameters via sql.Identifier/sql.Literal
  - Avoid raw SQL strings; use sql.Composed and sql.SQL for safety
* Asynchronous patterns:
  - Use async/await for database operations
  - Use contextlib.asynccontextmanager for async context managers
  - Use proper typing with AsyncGenerator and AsyncIterator
  - Follow proper async cleanup patterns with __aenter__/__aexit__ or aclose()

## Dependencies
* psycopg[pool] - PostgreSQL driver with connection pooling
* pydantic - Data validation and settings management
* sentence_transformers - Vector embedding generation
* pgvector - PostgreSQL vector extension
* asyncstdlib - Async utilities
* orjson - Fast JSON serialization/deserialization
