from pgraf import graph, postgres
from tests import common


class GraphTestCase(common.PostgresTestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.graph = graph.PGraf(common.postgres_url())

    async def asyncTearDown(self) -> None:
        await super().asyncTearDown()
        await self.graph.shutdown()

    async def test_setup(self) -> None:
        self.assertIsInstance(self.graph._postgres, postgres.Postgres)
