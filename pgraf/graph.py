import logging
import uuid

import psycopg
import pydantic
from psycopg import sql
from psycopg.types import json

from pgraf import embeddings, errors, models, postgres, queries

LOGGER = logging.getLogger(__name__)

NodeType = models.ContentNode | models.Node


class PGraf:
    """Manage and Search the Graph"""

    def __init__(
        self,
        url: pydantic.PostgresDsn,
        pool_min_size: int = 1,
        pool_max_size: int = 10,
    ) -> None:
        self._embeddings = embeddings.Embeddings()
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
            return await cursor.fetchone()  # type: ignore

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
            node: models.ContentNode = await cursor.fetchone()  # type: ignore
        await self._upsert_embeddings(node.id, node.content)
        return node

    async def delete_node(self, node_id: uuid.UUID) -> bool:
        """Retrieve a node by ID"""
        async with self._postgres.callproc(
            'pgraf.delete_node', {'id': node_id}
        ) as cursor:
            result: dict[str, int] = await cursor.fetchone()  # type: ignore
            return result['count'] == 1

    async def get_node(self, node_id: uuid.UUID) -> NodeType | None:
        """Retrieve a node by ID"""
        async with self._postgres.callproc(
            'pgraf.get_node', {'id': node_id}
        ) as cursor:
            if cursor.rowcount == 1:
                data: dict = await cursor.fetchone()  # type: ignore
                if data['type'] == 'content':
                    return models.ContentNode.model_validate(data)
                return models.Node.model_validate(data)
            return None

    async def get_nodes(
        self,
        properties: dict | None = None,
        node_types: list[str] | None = None,
    ) -> list[NodeType]:
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
            return await self._process_node_results(cursor)

    async def update_node(self, node: models.Node) -> models.Node:
        """Update a node"""
        async with self._postgres.callproc(
            'pgraf.update_node', node, models.Node
        ) as cursor:
            return await cursor.fetchone()  # type: ignore

    async def update_content_node(
        self, node: models.ContentNode
    ) -> models.ContentNode:
        """Update a node, recreating the embeddings and vectors"""
        async with self._postgres.callproc(
            'pgraf.update_content_node', node, models.ContentNode
        ) as cursor:
            node: models.ContentNode = await cursor.fetchone()  # type: ignore
        await self._upsert_embeddings(node.id, node.content)
        return node

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
                'properties': properties or {},
            }
        )
        async with self._postgres.callproc(
            'pgraf.add_edge', value, models.Edge
        ) as cursor:
            return await cursor.fetchone()  # type: ignore

    async def delete_edge(self, source: uuid.UUID, target: uuid.UUID) -> bool:
        """Remove an edge, severing the relationship between two nodes"""
        async with self._postgres.callproc(
            'pgraf.delete_edge', {'source': source, 'target': target}
        ) as cursor:
            result: dict[str, int] = await cursor.fetchone()  # type: ignore
            return result['count'] == 1

    async def get_edge(
        self, source: uuid.UUID, target: uuid.UUID
    ) -> models.Edge:
        """Add an edge, linking two nodes in the graph"""
        async with self._postgres.callproc(
            'pgraf.get_edge', {'source': source, 'target': target}, models.Edge
        ) as cursor:
            return await cursor.fetchone()  # type: ignore

    async def update_edge(self, edge: models.Edge) -> models.Edge:
        """Update an edge"""
        async with self._postgres.callproc(
            'pgraf.update_edge', edge, models.Edge
        ) as cursor:
            return await cursor.fetchone()  # type: ignore

    async def search(
        self,
        query: str,
        properties: dict | None = None,
        node_types: list[str] | None = None,
        similarity_threshold: float = 0.1,
        limit: int = 10,
    ) -> list:
        """Search the content nodes in the graph, optionally filtering by
        properties, node types, and the edges labels.

        """
        vector = self._embeddings.get(query)
        if len(vector) > 1:
            LOGGER.warning(
                'Search text embeddings returned %i vector arrays', len(vector)
            )
        async with self._postgres.callproc(
            'pgraf.search',
            {
                'query': query,
                'embeddings': vector[0],
                'properties': json.Jsonb(properties) if properties else None,
                'node_types': node_types,
                'similarity': similarity_threshold,
                'limit': limit,
            },
        ) as cursor:
            return await self._process_node_results(cursor)

    async def traverse(
        self,
        start_node: uuid.UUID,
        edge_labels: list[str] | None = None,
        direction: str = 'outgoing',
        max_depth: int = 100,
    ) -> list[tuple[NodeType, models.Edge | None]]:
        """Traverse the graph from a starting node"""
        results = []
        async with self._postgres.callproc(
            'pgraf.traverse',
            {
                'start_node': start_node,
                'direction': direction,
                'max_depth': max_depth,
                'edge_labels': edge_labels or [],
            },
        ) as cursor:
            rows: list[dict] = await cursor.fetchall()  # type: ignore
            for row in rows:
                edge_dict, node_dict = {}, {}
                for key, value in row.items():
                    if key.startswith('edge_') and value is not None:
                        edge_dict[key[5:]] = value
                    elif key.startswith('node_'):
                        node_dict[key[5:]] = value
                edge: models.Edge | None = None
                if edge_dict:
                    edge = models.Edge.model_validate(edge_dict)
                node: NodeType
                if node_dict['type'] == 'content':
                    node = models.ContentNode.model_validate(node_dict)
                else:
                    node = models.Node.model_validate(node_dict)
                results.append((node, edge))
        return results

    async def shutdown(self) -> None:
        """Gracefully shutdown any open connections"""
        await self._postgres.shutdown()

    async def _process_node_results(
        self, cursor: psycopg.AsyncCursor
    ) -> list[NodeType]:
        results: list[NodeType] = []
        rows: list[dict] = await cursor.fetchall()  # type: ignore
        for row in rows:
            if row['type'] == 'content':
                results.append(models.ContentNode.model_validate(row))
            else:
                results.append(models.Node.model_validate(row))
        return results

    async def _upsert_embeddings(
        self, node_id: uuid.UUID, content: str
    ) -> None:
        """Chunk the content and write the embeddings"""
        async with self._postgres.execute(
            queries.DELETE_EMBEDDINGS, {'node': node_id}
        ) as cursor:
            LOGGER.debug(
                'Deleted %i stale embeddings for %s', cursor.rowcount, node_id
            )
        for offset, value in enumerate(self._embeddings.get(content)):
            async with self._postgres.callproc(
                'pgraf.add_embedding',
                {'node': node_id, 'chunk': offset, 'value': value},
            ) as cursor:
                result: dict[str, bool] = await cursor.fetchone()  # type: ignore
                if not result['success']:
                    raise errors.DatabaseError('Failed to insert embedding')
