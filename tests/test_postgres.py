import datetime
import json
import random
import unittest
import uuid

import psycopg_pool
import pydantic
from psycopg import sql

from pgraf import errors, postgres

TEST_TABLE = """\
CREATE TABLE public.test (
    id          UUID PRIMARY KEY,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    value       INT NOT NULL,
    title       TEXT,
    labels      TEXT[]
);
"""

INSERT_TEST_RECORD = """
INSERT INTO public.test (id, created_at, value, title, labels)
     VALUES (%(id)s, %(created_at)s, %(value)s, %(title)s, %(labels)s)
  RETURNING *;
"""


class TestModel(pydantic.BaseModel):
    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    created_at: datetime.datetime = pydantic.Field(
        default_factory=lambda: datetime.datetime.now(tz=datetime.UTC)
    )
    value: int = pydantic.Field(default_factory=lambda: random.randint(0, 100))  # noqa: S311
    title: str | None = None
    labels: list[str] | None = None


class PostgresTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.postgres = postgres.Postgres()
        async with self.postgres.cursor() as cursor:
            await cursor.execute(TEST_TABLE)

    async def asyncTearDown(self) -> None:
        async with self.postgres.cursor() as cursor:
            await cursor.execute('DROP TABLE public.test')
        await self.postgres.close_pool()

    async def test_pool_is_created(self) -> None:
        self.assertIsInstance(
            self.postgres._pool, psycopg_pool.AsyncConnectionPool
        )

    async def test_pool_open(self) -> None:
        # Pool should already be open
        result = await self.postgres.open_pool()
        self.assertFalse(result)

    async def test_execute(self) -> None:
        item = TestModel()
        async with postgres.execute(
            INSERT_TEST_RECORD, item.model_dump(), TestModel
        ) as cursor:
            result = await cursor.fetchone()
        self.assertEqual(result.id, item.id)
        self.assertEqual(result.created_at, item.created_at)
        self.assertEqual(result.value, item.value)

    async def test_execute_with_sql_composable(self) -> None:
        item = TestModel()
        composed_query = sql.Composed(
            [
                sql.SQL('INSERT INTO'),
                sql.Identifier('public.test'),
                sql.SQL('(id, created_at, value)'),
                sql.SQL('VALUES'),
                sql.SQL('(%(id)s, %(created_at)s, %(value)s) RETURNING *'),
            ]
        )
        async with postgres.execute(
            composed_query, item.model_dump(), TestModel
        ) as cursor:
            result = await cursor.fetchone()
        self.assertEqual(result.id, item.id)
        self.assertEqual(result.created_at, item.created_at)
        self.assertEqual(result.value, item.value)

    async def test_execute_with_database_error(self) -> None:
        with self.assertRaises(errors.DatabaseError):
            async with postgres.execute(
                'SELECT * FROM nonexistent_table', {}
            ) as cursor:
                await cursor.fetchone()
