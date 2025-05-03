import json
import pathlib
import random
import subprocess
import unittest

import pydantic
import yaml

from pgraf import postgres

DATA_DIR = pathlib.Path(__file__).parent / 'data'


def load_test_data(filename: str) -> list | dict:
    with (DATA_DIR / filename).open('r') as handle:
        return yaml.safe_load(handle)


class PostgresTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.postgres = postgres.Postgres(postgres_url())

    async def asyncTearDown(self) -> None:
        if self.postgres._pool:
            async with self.postgres.cursor() as cursor:
                await cursor.execute('TRUNCATE TABLE pgraf.nodes CASCADE')
        await self.postgres.shutdown()


def _docker_port() -> int:
    result = subprocess.run(  # noqa: S603
        ['docker', 'compose', 'ps', '--format', 'json', 'postgres'],  # noqa: S607
        capture_output=True,
    )
    process = json.loads(result.stdout)
    return process['Publishers'][0]['PublishedPort']


def test_embeddings() -> list[float]:
    """Returns a list of 1536 floats for testing."""
    return [float(f'{random.random()}') for _v in range(1536)]  # noqa: S311


def postgres_url() -> pydantic.PostgresDsn:
    """Return connection parameters for database in either environment"""
    return pydantic.PostgresDsn(
        f'postgres://postgres:password@localhost:{_docker_port()}/postgres'
    )
