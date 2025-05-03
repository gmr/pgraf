import logging
import uuid

import pydantic
from psycopg import sql
from psycopg.types import json

from pgraf import embeddings, models, postgres, queries

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
        value = models.Node.model_validate(
            {'type': node_type, 'properties': properties}
        )
        async with self._postgres.callproc(
            'pgraf.add_node', value, models.Node
        ) as cursor:
            return await cursor.fetchone()

    async def add_content_node(
        self,
        title: str,
        source: str,
        mimetype: str,
        content: str,
        url: str | None,
        properties: dict | None = None,
    ) -> models.ContentNode:
        """Add a content based node to the graph"""
        value = models.ContentNode.model_validate(
            {
                'title': title,
                'source': source,
                'mimetype': mimetype,
                'content': content,
                'url': url,
                'properties': properties,
            }
        )
        async with self._postgres.callproc(
            'pgraf.add_content_node', value, models.ContentNode
        ) as cursor:
            return await cursor.fetchone()

    async def delete_node(self, node_id: uuid.UUID) -> bool:
        """Retrieve a node by ID"""
        async with self._postgres.callproc(
            'pgraf.delete_node', {'id': node_id}
        ) as cursor:
            result = await cursor.fetchone()
            return result['count'] == 1

    async def get_node(
        self, node_id: uuid.UUID
    ) -> models.Node | models.ContentNode | None:
        """Retrieve a node by ID"""
        async with self._postgres.callproc(
            'pgraf.get_node', {'id': node_id}
        ) as cursor:
            if cursor.rowcount == 1:
                data = await cursor.fetchone()
                if data['type'] == 'content':
                    return models.ContentNode.model_validate(data)
                return models.Node.model_validate(data)
            return None

    async def get_nodes(
        self,
        properties: dict | None = None,
        node_types: list[str] | None = None,
    ) -> list[models.Node | models.ContentNode]:
        """Get all nodes matching the criteria"""
        statement: list[str | sql.Composable] = [
            sql.SQL(queries.GET_NODES.strip() + ' ')  # type: ignore
        ]
        where = []
        if properties:
            where.append(sql.SQL('properties @> %(properties)s'))
        if node_types:
            where.append(sql.SQL('type = ANY(%(node_types)s)'))
        if where:
            statement.append(sql.SQL('WHERE '))
            statement.append(sql.SQL(' AND ').join(where))
        async with self._postgres.execute(
            sql.Composed(statement),
            {'properties': json.Jsonb(properties), 'node_types': node_types},
        ) as cursor:
            results = []
            for row in await cursor.fetchall():
                if row['type'] == 'content':
                    results.append(models.ContentNode.model_validate(row))
                else:
                    results.append(models.Node.model_validate(row))
        return results

    async def update_node(self, node: models.Node) -> models.Node:
        """Update a node"""
        async with self._postgres.callproc(
            'pgraf.update_node', node, models.Node
        ) as cursor:
            return await cursor.fetchone()

    async def update_content_node(
        self, node: models.ContentNode
    ) -> models.ContentNode:
        """Update a node, recreating the embeddings and vectors"""
        async with self._postgres.callproc(
            'pgraf.update_content_node', node, models.ContentNode
        ) as cursor:
            return await cursor.fetchone()

    async def add_edge(
        self,
        source: uuid.UUID,
        target: uuid.UUID,
        label: str,
        properties: dict | None = None,
    ) -> models.Edge:
        """Add an edge, linking two nodes in the graph"""
        value = models.Edge.model_validate(
            {
                'source': source,
                'target': target,
                'label': label,
                'properties': properties,
            }
        )
        async with self._postgres.callproc(
            'pgraf.add_edge', value, models.Edge
        ) as cursor:
            return await cursor.fetchone()

    async def delete_edge(self, source: uuid.UUID, target: uuid.UUID) -> bool:
        """Remove an edge, severing the relationship between two nodes"""
        async with self._postgres.callproc(
            'pgraf.delete_edge', {'source': source, 'target': target}
        ) as cursor:
            result = await cursor.fetchone()
            return result['count'] == 1

    async def update_edge(self, edge: models.Edge) -> models.Edge:
        """Update an edge"""
        async with self._postgres.callproc(
            'pgraf.update_edge', edge, models.Edge
        ) as cursor:
            return await cursor.fetchone()

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

    async def traverse(
        self,
        start_node: uuid.UUID,
        edge_labels: list[str] | None = None,
        direction: str = 'outgoing',
        max_depth: int = 1,
    ) -> list[tuple[models.Node, models.Edge]]:
        """Traverse the graph from a starting node"""
        ...

    async def shutdown(self) -> None:
        """Gracefully shutdown any open connections"""
        await self._postgres.shutdown()
