import datetime
import re

import pydantic


def current_timestamp() -> datetime.datetime:
    """Return the current timestamp"""
    return datetime.datetime.now(tz=datetime.UTC)


def sanitize(url: str | pydantic.AnyUrl | pydantic.PostgresDsn) -> str:
    """Mask passwords in URLs for security.

    Args:
        url: Input string that may contain URLs with passwords

    Returns:
        Text with passwords in URLs replaced with asterisks

    """
    pattern = re.compile(r'(\w+?://[^:@]+:)([^@]+)(@)')
    return pattern.sub(r'\1******\3', str(url))
