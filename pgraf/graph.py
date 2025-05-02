import logging
import uuid

import pydantic

from pgraf import embeddings, models, postgres

LOGGER = logging.getLogger(__name__)


class PGraf:
    """Manage and Search the Graph"""

    def __init__(
        self,
        url: pydantic.PostgresDsn,
        pool_min_size: int = 1,
        pool_max_size: int = 10,
        openapi_api_key: str | None = None,
    ) -> None:
        self._embeddings = embeddings.Embeddings(openapi_api_key)
        self._postgres = postgres.Postgres(url, pool_min_size, pool_max_size)

    async def add_node(
        self, node_type: str, properties: dict | None = None
    ) -> models.Node:
        """Add a node to the graph"""
        ...

    async def add_document_node(
        self,
        title: str,
        content: str,
        url: str,
        properties: dict | None = None,
    ) -> models.DocumentNode:
        """Add a document based node to the graph"""
        ...

    async def add_edge(
        self, source: uuid.UUID, target: uuid.UUID, label: str
    ) -> models.Edge:
        """Add an edge, linking two nodes in the graph"""
        ...

    async def remove_node(self, node: uuid.UUID) -> None:
        """Remove a node from the graph"""
        ...

    async def remove_document_node(self, node: uuid.UUID) -> None:
        """Remove a document node from the graph"""
        await self.remove_node(node)

    async def remove_edge(self, source: uuid.UUID, target: uuid.UUID) -> None:
        """Remove an edge, severing the relationship between two nodes"""
        ...

    async def update_node(self, node: models.Node) -> models.Node:
        """Update a node"""
        ...

    async def update_document_node(
        self, node: models.DocumentNode
    ) -> models.DocumentNode:
        """Update a node, recreating the embeddings and vectors"""
        ...

    async def search(
        self,
        query: str,
        properties: dict | None = None,
        node_types: list[str] | None = None,
        edge_labels: list[str] | None = None,
    ) -> list:
        """Search the graph, optionally filtering by properties, node types,
        and the edges labels.

        """
        ...

    async def shutdown(self) -> None:
        """Gracefully shutdown any open connections"""
        await self._postgres.shutdown()
