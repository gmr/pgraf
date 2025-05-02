import json
import os
import subprocess

import pydantic


def _docker_port() -> int:
    result = subprocess.run(  # noqa: S603
        ['docker', 'compose', 'ps', '--format', 'json', 'postgres'],  # noqa: S607
        capture_output=True,
    )
    process = json.loads(result.stdout)
    return process['Publishers'][0]['PublishedPort']


def postgres_url() -> pydantic.PostgresDsn:
    """Return connection parameters for database in either environment"""
    host = 'localhost'
    user = 'postgres'
    password = 'password'  # noqa: S105
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        host = 'postgres'
        port = 5432
    else:
        port = _docker_port()
    return pydantic.PostgresDsn(
        f'postgres://{user}:{password}@{host}:{port}/postgres'
    )
