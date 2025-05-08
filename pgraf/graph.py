import datetime
import logging
import typing
import uuid

import pydantic
from psycopg import sql
from psycopg.types import json

from pgraf import embeddings, errors, models, postgres, queries

LOGGER = logging.getLogger(__name__)


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

    async def initialize(self) -> None:
        """Ensure the database is connected and ready to go."""
        await self._postgres.initialize()

    async def aclose(self) -> None:
        """Close the Postgres connection pool."""
        await self._postgres.aclose()

    async def add_node(
        self,
        labels: list[str],
        properties: dict | None = None,
        created_at: datetime.datetime | None = None,
        modified_at: datetime.datetime | None = None,
        mimetype: str | None = None,
        content: str | None = None,
    ) -> models.Node:
        """Add a node to the graph"""
        value = models.Node(
            labels=labels,
            properties=properties or {},
            mimetype=mimetype,
            content=content,
        )
        if created_at is not None:
            value.created_at = created_at
        if modified_at is not None:
            value.modified_at = modified_at
        async with self._postgres.callproc(
            'pgraf.add_node', value, models.Node
        ) as cursor:
            result = await cursor.fetchone()  # type: ignore
        if content is not None:
            await self._upsert_embeddings(value.id, value.content)
        return result

    async def delete_node(self, node_id: uuid.UUID) -> bool:
        """Retrieve a node by ID"""
        async with self._postgres.callproc(
            'pgraf.delete_node', {'id': node_id}
        ) as cursor:
            result: dict[str, int] = await cursor.fetchone()  # type: ignore
            return result['count'] == 1

    async def get_node(self, node_id: uuid.UUID | None) -> models.Node | None:
        """Retrieve a node by ID"""
        async with self._postgres.callproc(
            'pgraf.get_node', {'id': node_id}, models.Node
        ) as cursor:
            if cursor.rowcount == 1:
                return await cursor.fetchone()
            return None

    async def get_node_labels(self) -> list[str]:
        """Retrieve all of the node types in the graph"""
        return await self._get_labels('nodes')

    async def get_node_properties(self) -> list[str]:
        """Retrieve the distincty property names across all nodes"""
        return await self._get_properties('nodes')

    async def get_nodes(
        self, properties: dict | None = None, labels: list[str] | None = None
    ) -> typing.AsyncGenerator[models.Node, None]:
        """Get all nodes matching the criteria"""
        statement: list[str | sql.Composable] = [
            sql.SQL(queries.GET_NODES) + sql.SQL(' ')  # type: ignore
        ]
        where = []
        parameters = {}
        if labels:
            parameters['labels'] = labels
            where.append(sql.SQL('labels && %(labels)s'))
        if properties:
            props = []
            for key, value in properties.items():
                props.append(
                    sql.SQL(
                        f"properties->>'{key}' = "  # type: ignore
                        f'%(props_{key})s'
                    )
                )
                parameters[f'props_{key}'] = value
            if len(props) > 1:
                where.append(
                    sql.SQL('(') + sql.SQL(' OR ').join(props) + sql.SQL(')')
                )
            else:
                where.append(props[0])
        if where:
            statement.append(sql.SQL('WHERE '))
            statement.append(sql.SQL(' AND ').join(where))
        async with self._postgres.execute(
            sql.Composed(statement), parameters, models.Node
        ) as cursor:
            async for row in cursor:
                yield models.Node.model_validate(row)

    async def update_node(self, node: models.Node) -> models.Node:
        """Update a node"""
        async with self._postgres.callproc(
            'pgraf.update_node', node, models.Node
        ) as cursor:
            result = await cursor.fetchone()  # type: ignore
        if result.content is not None:
            await self._upsert_embeddings(result.id, result.content)
        return result

    async def add_edge(
        self,
        source: uuid.UUID,
        target: uuid.UUID,
        labels: list[str] | None = None,
        properties: dict | None = None,
    ) -> models.Edge:
        """Add an edge, linking two nodes in the graph"""
        value = models.Edge(
            source=source,
            target=target,
            labels=labels or [],
            properties=properties or {},
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

    async def get_edge_labels(self) -> list[str]:
        """Retrieve all of the edge labels in the graph"""
        return await self._get_labels('edges')

    async def get_edge_properties(self) -> list[str]:
        """Retrieve all of the edge property names in the graph"""
        return await self._get_properties('edges')

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
        labels: list[str] | None = None,
        source: str | None = None,
        similarity_threshold: float = 0.1,
        limit: int = 10,
    ) -> list[models.SearchResult]:
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
                'labels': labels,
                'similarity': similarity_threshold,
                'source': source,
                'limit': limit,
            },
            models.SearchResult,
        ) as cursor:
            return await cursor.fetchall()

    async def traverse(
        self,
        start_node: uuid.UUID,
        node_labels: list[str] | None = None,
        edge_labels: list[str] | None = None,
        direction: str = 'outgoing',
        max_depth: int = 5,
        limit: int = 25,
    ) -> list[tuple[models.Node, models.Edge | None]]:
        """Traverse the graph from a starting node"""
        results = []
        async with self._postgres.callproc(
            'pgraf.traverse',
            {
                'start_node': start_node,
                'direction': direction,
                'max_depth': max_depth,
                'node_labels': node_labels or [],
                'edge_labels': edge_labels or [],
                'limit': limit,
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
                node = models.Node.model_validate(node_dict)
                edge: models.Edge | None = None
                if edge_dict:
                    edge = models.Edge.model_validate(edge_dict)
                results.append((node, edge))
        return results

    async def _get_labels(self, table: str) -> list[str]:
        """Dynamically construct the query to get distinct labels"""
        query = sql.Composed(
            [
                sql.SQL('SELECT DISTINCT unnest(labels) AS label'),
                sql.SQL(' FROM '),
                sql.SQL('.').join(
                    [sql.Identifier('pgraf'), sql.Identifier(table)]
                ),
                sql.SQL(' WHERE labels IS NOT NULL '),
                sql.SQL(' ORDER BY label'),
            ]
        )
        async with self._postgres.execute(query) as cursor:
            return [row['label'] for row in await cursor.fetchall()]  # type: ignore

    async def _get_properties(self, table: str) -> list[str]:
        """Retrieve the distincty property names across all nodes"""
        query = sql.Composed(
            [
                sql.SQL(
                    'SELECT DISTINCT jsonb_object_keys(properties) AS key'
                ),
                sql.SQL(' FROM '),
                sql.SQL('.').join(
                    [sql.Identifier('pgraf'), sql.Identifier(table)]
                ),
                sql.SQL(' WHERE properties IS NOT NULL'),
                sql.SQL(' ORDER BY key'),
            ]
        )
        async with self._postgres.execute(query) as cursor:
            return [row['key'] for row in await cursor.fetchall()]  # type: ignore

    async def _upsert_embeddings(
        self, node_id: uuid.UUID, content: str
    ) -> None:
        """Chunk the content and write the embeddings"""
        for offset, value in enumerate(self._embeddings.get(content)):
            async with self._postgres.callproc(
                'pgraf.add_embedding',
                {'node': node_id, 'chunk': offset, 'value': value},
            ) as cursor:
                result: dict[str, bool] = await cursor.fetchone()  # type: ignore
                if not result['success']:
                    raise errors.DatabaseError('Failed to insert embedding')
