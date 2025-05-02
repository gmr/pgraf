import contextlib
import logging
import re
import typing
from collections import abc

import psycopg
import psycopg_pool
import pydantic
from psycopg import rows, sql

from pgraf import utils

LOGGER = logging.getLogger(__name__)

Model = typing.TypeVar('Model', bound=pydantic.BaseModel)


class Postgres:
    _instance: typing.Self | None = None

    def __init__(
        self, url: pydantic.PostgresDsn, pool_min_size: int, pool_max_size: int
    ) -> None:
        self._url = str(url)
        self._pool = psycopg_pool.AsyncConnectionPool(
            self._url,
            kwargs={'autocommit': True, 'row_factory': rows.dict_row},
            max_size=pool_max_size,
            min_size=pool_min_size,
            open=False,
        )

    @classmethod
    def get_instance(
        cls,
        url: pydantic.PostgresDsn | None = None,
        pool_min_size: int = 1,
        pool_max_size: int = 10,
    ) -> typing.Self:
        """Get the instance of the database layer, passing in the URL
        and pool settings. You must pass the URL the first time you
        """
        if cls._instance is None:
            if url is None:
                raise AttributeError('You must pass `url` on the first call')
            cls._instance = cls(url, pool_min_size, pool_max_size)
        return cls._instance

    async def open_pool(self) -> bool:
        """Open the connection pool, returns False if the pool
        is already open.

        """
        if self._pool.closed:
            LOGGER.debug(
                'Opening connection pool to %s', utils.sanitize(self._url)
            )
            await self._pool.open(True, timeout=3.0)
            LOGGER.debug('Connection pool opened')
            return True
        return False

    async def close_pool(self) -> bool:
        """Close the connection pool, returns False if the pool
        is already closed.

        """
        if not self._pool.closed:
            LOGGER.debug('Closing connection pool')
            await self._pool.close()
            return True
        return False

    @contextlib.asynccontextmanager
    async def cursor(
        self,
        row_class: type[pydantic.BaseModel] | None = None,
        row_factory: rows.RowFactory = rows.dict_row,
    ) -> abc.AsyncGenerator[psycopg.AsyncCursor]:
        """Get a cursor for Postgres."""
        if row_class:
            factory = rows.class_row(row_class)
        else:
            factory = row_factory
        if self._pool.closed:
            await self.open_pool()
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=factory) as crs:
                yield crs



@contextlib.asynccontextmanager
async def execute(
    query: str | sql.Composable,
    parameters: dict | None = None,
    row_class: type[pydantic.BaseModel] | None = None,
    row_factory: rows.RowFactory = rows.dict_row,
) -> typing.AsyncIterator[psycopg.AsyncCursor]:
    """Wrapper context manager for making executing queries easier."""
    postgres = Postgres.get_instance()
    async with postgres.cursor(row_class, row_factory) as cursor:
        if isinstance(query, sql.Composable):
            query = query.as_string(cursor)
        query = re.sub(r'\s+', ' ', query).encode('utf-8')
        try:
            await cursor.execute(query, parameters or {})
            yield cursor
        except psycopg.DatabaseError as err:
            raise errors.DatabaseError(str(err)) from err
