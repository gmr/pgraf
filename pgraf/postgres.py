import asyncio
import contextlib
import logging
import re
import typing
from collections import abc

import psycopg
import psycopg_pool
import pydantic
from pgvector.psycopg import register_vector_async
from psycopg import rows, sql

from pgraf import errors, queries, utils

LOGGER = logging.getLogger(__name__)

Model = typing.TypeVar('Model', bound=pydantic.BaseModel)
AsyncCursor = psycopg.AsyncCursor[Model | tuple[typing.Any, ...]]
RowFactory = rows.BaseRowFactory[Model | tuple[typing.Any, ...]]


class Postgres:
    _pool: psycopg_pool.AsyncConnectionPool | None

    def __init__(
        self,
        url: pydantic.PostgresDsn,
        pool_min_size: int = 1,
        pool_max_size: int = 10,
    ) -> None:
        self._lock = asyncio.Lock()
        self._pool = psycopg_pool.AsyncConnectionPool(
            str(url),
            kwargs={'autocommit': True, 'row_factory': rows.dict_row},
            max_size=pool_max_size,
            min_size=pool_min_size,
            open=False,
            configure=self._configure_vector,
        )
        self._url = str(url)

    async def initialize(self) -> None:
        """Initialize the connection pool"""
        async with self._lock:
            await self._open_pool()

    async def aclose(self) -> None:
        """Close the connection pool, returns False if the pool
        is already closed.

        """
        async with self._lock:
            if self._pool and not self._pool.closed:
                LOGGER.debug('Closing connection pool')
                await self._pool.close()
            self._pool = None

    @contextlib.asynccontextmanager
    async def callproc(
        self,
        proc_name: str,
        parameters: dict | pydantic.BaseModel,
        row_class: type[pydantic.BaseModel] | None = None,
    ) -> abc.AsyncGenerator[AsyncCursor]:
        """Call a stored procedure"""
        statement = await self._callproc_statement(proc_name)
        if hasattr(parameters, 'model_dump'):
            parameters = parameters.model_dump()
        async with self.execute(statement, parameters, row_class) as cursor:
            yield cursor

    @contextlib.asynccontextmanager
    async def cursor(
        self, row_class: type[pydantic.BaseModel] | None = None
    ) -> abc.AsyncGenerator[AsyncCursor]:
        """Get a cursor for Postgres."""
        if not self._pool:
            raise RuntimeError('Postgres instance already closed')
        elif self._pool.closed:
            await self._open_pool()
        async with self._pool.connection() as conn:
            async with conn.cursor(
                row_factory=rows.class_row(row_class)
                if row_class
                else rows.dict_row
            ) as cursor:
                yield cursor

    @contextlib.asynccontextmanager
    async def execute(
        self,
        query: str | sql.Composable,
        parameters: dict | None = None,
        row_class: type[pydantic.BaseModel] | None = None,
    ) -> typing.AsyncIterator[AsyncCursor]:
        """Wrapper context manager for making executing queries easier."""
        async with self.cursor(row_class) as cursor:
            if isinstance(query, sql.Composable):
                query = query.as_string(cursor)
            composed = re.sub(r'\s+', ' ', query).encode('utf-8')
            try:
                await cursor.execute(composed, parameters or {})
                yield cursor
            except psycopg.DatabaseError as err:
                raise errors.DatabaseError(str(err)) from err

    async def _open_pool(self) -> None:
        """Open the connection pool, returns False if the pool
        is already open.

        """
        if self._pool and self._pool.closed:
            LOGGER.debug(
                'Opening connection pool to %s', utils.sanitize(self._url)
            )
            await self._pool.open(True, timeout=3.0)
            LOGGER.debug('Connection pool opened')

    async def _callproc_columns(
        self, proc_name: str, schema_name: str = 'public'
    ) -> typing.AsyncGenerator[tuple[str, str | None], None]:
        """Get the columns for a stored procedure in order, expects the
        convention of _in for an input column name

        """
        async with self.execute(
            queries.PROC_NAMES,
            {'proc_name': proc_name, 'schema_name': schema_name},
        ) as cursor:
            if not cursor.rowcount:
                raise errors.DatabaseError(
                    f'Failed to fetch stored procedure: '
                    f'{schema_name}.{proc_name}'
                )
            result: list[dict] = await cursor.fetchall()  # type: ignore
            for row in result:
                if row['arg_type'] == 'vector':
                    yield row['arg_name'], None
                else:
                    yield row['arg_name'], row['arg_type']

    async def _callproc_statement(self, proc_name: str) -> sql.Composed:
        """Generate the statement to invoke the stored procedure"""
        schema = 'public'
        if '.' in proc_name:
            schema, proc_name = proc_name.split('.')
        statement: list[str | sql.Composable] = [
            sql.SQL('SELECT * FROM '),
            sql.Identifier(schema),
            sql.SQL('.'),
            sql.Identifier(proc_name),
            sql.SQL('('),
        ]
        async for name, col_type in self._callproc_columns(proc_name, schema):
            if col_type is None:
                statement.append(sql.Placeholder(name))
            else:
                statement.append(
                    sql.Placeholder(name) + sql.SQL('::') + sql.SQL(col_type)  # type: ignore
                )
            statement.append(sql.SQL(', '))
        if len(statement) > 5:  # Strip the last ,
            statement = statement[:-1]
        statement.append(sql.SQL(')'))
        LOGGER.debug('callproc: %s', sql.Composed(statement).as_string())
        return sql.Composed(statement)

    @staticmethod
    async def _configure_vector(conn: psycopg.AsyncConnection) -> None:
        await register_vector_async(conn)
