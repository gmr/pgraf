When we write Python code:
- We follow the [PEP 8](https://pep8.org/) style guide.
- We import modules instead of names. For example, we `from urllib import parse` and use `parse.urlsplit()` instead of `from urllib.parse import urlsplit`.
- We always use Python 3.10 style type hints. For example: `foo: str | None = None`
- When extending a method, always call the superclass method.
