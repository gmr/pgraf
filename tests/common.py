import json
import subprocess
import unittest

import pydantic

from pgraf import postgres


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


def postgres_url() -> pydantic.PostgresDsn:
    """Return connection parameters for database in either environment"""
    return pydantic.PostgresDsn(
        f'postgres://postgres:password@localhost:{_docker_port()}/postgres'
    )
