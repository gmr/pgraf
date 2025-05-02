import datetime
import random
import uuid

import psycopg_pool
import pydantic
from psycopg import sql

from pgraf import errors, utils
from tests import common

TEST_TABLE = """\
CREATE TABLE IF NOT EXISTS public.test (
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


class Model(pydantic.BaseModel):
    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    created_at: datetime.datetime = pydantic.Field(
        default_factory=utils.current_timestamp
    )
    value: int = pydantic.Field(default_factory=lambda: random.randint(0, 100))  # noqa: S311
    title: str | None = None
    labels: list[str] | None = None


class PostgresTestCase(common.PostgresTestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        async with self.postgres.cursor() as cursor:
            await cursor.execute(TEST_TABLE)

    async def asyncTearDown(self) -> None:
        if self.postgres._pool:
            async with self.postgres.cursor() as cursor:
                await cursor.execute('DROP TABLE public.test')
        await super().asyncTearDown()

    async def test_pool_is_created(self) -> None:
        self.assertIsInstance(
            self.postgres._pool, psycopg_pool.AsyncConnectionPool
        )

    async def test_pool_is_opened(self) -> None:
        await self.postgres._open_pool()
        self.assertFalse(self.postgres._pool.closed)

    async def test_execute(self) -> None:
        item = Model()
        async with self.postgres.execute(
            INSERT_TEST_RECORD, item.model_dump(), Model
        ) as cursor:
            result = await cursor.fetchone()
        self.assertEqual(result.id, item.id)
        self.assertEqual(result.created_at, item.created_at)
        self.assertEqual(result.value, item.value)

    async def test_execute_with_sql_composable(self) -> None:
        item = Model()
        composed_query = sql.Composed(
            [
                sql.SQL('INSERT INTO '),
                sql.Identifier('public'),
                sql.SQL('.'),
                sql.Identifier('test'),
                sql.SQL('(id, created_at, value)'),
                sql.SQL(' VALUES '),
                sql.SQL('(%(id)s, %(created_at)s, %(value)s) RETURNING *'),
            ]
        )
        async with self.postgres.execute(
            composed_query, item.model_dump(), Model
        ) as cursor:
            result = await cursor.fetchone()
        self.assertEqual(result.id, item.id)
        self.assertEqual(result.created_at, item.created_at)
        self.assertEqual(result.value, item.value)

    async def test_execute_with_database_error(self) -> None:
        with self.assertRaises(errors.DatabaseError):
            async with self.postgres.execute(
                'SELECT * FROM nonexistent_table', {}
            ) as cursor:
                await cursor.fetchone()

    async def test_shutdown_double_call(self) -> None:
        await self.postgres.shutdown()
        self.assertIsNone(self.postgres._pool)
        with self.assertRaises(RuntimeError):
            async with self.postgres.execute('SELECT 1') as _:
                ...
