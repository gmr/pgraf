# Contributing

Contributions to pgraf are welcome! Here's how to get started.

## Development Setup

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/your-username/pgraf.git
   cd pgraf
   ```

3. Install development dependencies:

   ```bash
   pip install -e ".[dev]"
   ```

4. Set up pre-commit hooks:

   ```bash
   pre-commit install
   ```

5. Start the development database:

   ```bash
   docker-compose up -d
   ```

## Development Workflow

1. Create a branch for your feature:

   ```bash
   git checkout -b feature-name
   ```

2. Make your changes
3. Run tests:

   ```bash
   pytest
   ```

4. Run type checking:

   ```bash
   mypy pgraf tests
   ```

5. Run linting:

   ```bash
   ruff check .
   ```

6. Format code:

   ```bash
   ruff format .
   ```

7. Commit your changes
8. Push your branch and create a pull request

## Code Style Guidelines

* Follow PEP-8 with 79 character line length (enforced by ruff)
* Use single quotes for strings, double quotes for docstrings
* Write Google-style docstrings
* Include type annotations for all functions and methods
* Run formatting with ruff before committing

## Testing

* Write unit tests for all new functionality
* Ensure all tests pass before submitting a pull request
* Maintain test coverage above 90%
