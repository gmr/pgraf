import logging

import pydantic

from pgraf import postgres

LOGGER = logging.getLogger(__name__)


class PGraf:
    """Manage and Search the Graph"""

    def __init__(
        self,
        url: pydantic.PostgresDsn,
        pool_min_size: int = 1,
        pool_max_size: int = 10,
    ) -> None:
        self._postgres = postgres.Postgres(url, pool_min_size, pool_max_size)

    async def shutdown(self) -> None:
        await self._postgres.shutdown()
