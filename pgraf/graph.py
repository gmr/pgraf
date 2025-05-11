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
    """Manage and Search the Property Graph.

    The PGraf class is the main entry point for interacting with the graph
    database. It provides methods for adding nodes and edges, querying,
    traversing the graph, and performing vector similarity searches.

    Args:
        url: PostgreSQL connection URL
        pool_min_size: Minimum number of connections in the pool
        pool_max_size: Maximum number of connections in the pool
    """

    def __init__(
        self,
        url: pydantic.PostgresDsn,
        pool_min_size: int = 1,
        pool_max_size: int = 10,
    ) -> None:
        """Initialize a new PGraf instance.

        Args:
            url: PostgreSQL connection URL
            pool_min_size: Minimum number of connections in the pool
            pool_max_size: Maximum number of connections in the pool
        """
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
            result: models.Node = await cursor.fetchone()  # type: ignore
        if value.content is not None:
            await self._add_embeddings(value.id, value.content)
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
                return await cursor.fetchone()  # type: ignore
            return None

    async def get_node_labels(self) -> list[str]:
        """Retrieve all of the node types in the graph"""
        return await self._get_labels('nodes')

    async def get_node_properties(self) -> list[str]:
        """Retrieve the distincty property names across all nodes"""
        return await self._get_properties('nodes')

    async def get_nodes(
        self, labels: list[str] | None = None, properties: dict | None = None
    ) -> typing.AsyncGenerator[models.Node, None]:
        """Get all nodes matching the criteria"""
        statement, parameters = self._build_statement(
            queries.GET_NODES, labels, properties
        )
        async with self._postgres.execute(
            statement, parameters, models.Node
        ) as cursor:
            async for row in cursor:
                yield models.Node.model_validate(row)

    async def update_node(self, node: models.Node) -> models.Node:
        """Update a node"""
        async with self._postgres.callproc(
            'pgraf.update_node', node, models.Node
        ) as cursor:
            result: models.Node = await cursor.fetchone()  # type: ignore
        if result.content is not None:
            await self._add_embeddings(result.id, result.content)
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
        """Remove an edge, severing the relationship between two nodes

        Note: This is a directional operation. It only removes the edge going
        from source to target, not from target to source.
        """
        async with self._postgres.callproc(
            'pgraf.delete_edge', {'source': source, 'target': target}
        ) as cursor:
            result: dict[str, int] = await cursor.fetchone()  # type: ignore
            return result['count'] == 1

    async def get_edge(
        self, source: uuid.UUID, target: uuid.UUID
    ) -> models.Edge | None:
        """Retrieve an edge from source to target

        Note: This is a directional operation. It only retrieves the edge going
        from source to target, not from target to source.
        """
        async with self._postgres.callproc(
            'pgraf.get_edge', {'source': source, 'target': target}, models.Edge
        ) as cursor:
            if cursor.rowcount == 0:
                return None
            return await cursor.fetchone()  # type: ignore

    async def get_edges(
        self, labels: list[str] | None = None, properties: dict | None = None
    ) -> typing.AsyncGenerator[models.Edge, None]:
        """Get edges by criteria"""
        statement, parameters = self._build_statement(
            queries.GET_EDGES, labels, properties
        )
        async with self._postgres.execute(
            statement, parameters, models.Edge
        ) as cursor:
            async for row in cursor:
                yield models.Edge.model_validate(row)

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
        labels: list[str] | None = None,
        properties: dict | None = None,
        similarity_threshold: float = 0.1,
        limit: int = 10,
        offset: int = 0,
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
                'labels': labels,
                'properties': json.Jsonb(properties) if properties else None,
                'embeddings': vector[0],
                'similarity': similarity_threshold,
                'limit': limit,
                'offset': offset,
            },
            models.SearchResult,
        ) as cursor:
            results: list[models.SearchResult] = await cursor.fetchall()  # type: ignore
            return results

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
        results: list[tuple[models.Node, models.Edge | None]] = []
        visited_nodes = set()  # Track visited nodes to avoid duplicates

        # Recursive helper function to implement depth-first traversal
        async def traverse_recursive(node_id, current_depth=0, path_edge=None):
            # Check the limit
            if len(results) >= limit:
                return

            # Check max depth
            if current_depth > max_depth:
                return

            # Check if we've visited this node
            if node_id in visited_nodes:
                return

            # Mark this node as visited
            visited_nodes.add(node_id)

            # Get the current node
            current_node = await self.get_node(node_id)
            if not current_node:
                return

            # Apply node label filtering
            if node_labels and not any(
                label in current_node.labels for label in node_labels
            ):
                # Only filter at depth > 0 to ensure starting node is included
                if current_depth > 0:
                    return

            # Add this node to results
            results.append((current_node, path_edge))

            if current_depth >= max_depth:
                return

            # Build SQL query based on direction
            if direction == 'outgoing':
                query = sql.SQL(
                    'SELECT * FROM pgraf.edges WHERE source = %(node_id)s'
                )
            elif direction == 'incoming':
                query = sql.SQL(
                    'SELECT * FROM pgraf.edges WHERE target = %(node_id)s'
                )
            else:  # both
                query = sql.SQL(
                    """\
                    SELECT *
                      FROM pgraf.edges
                     WHERE source = %(node_id)s
                        OR target = %(node_id)s
                    """
                )

            # Get all edges connected to this node
            async with self._postgres.execute(
                query, {'node_id': node_id}
            ) as cursor:
                edges = await cursor.fetchall()

                # Process each edge
                for edge_row in edges:
                    # Skip edges that don't match filter criteria
                    if edge_labels and not any(
                        label in edge_row['labels'] for label in edge_labels
                    ):
                        continue

                    # Create the edge model
                    edge = models.Edge(
                        source=edge_row['source'],
                        target=edge_row['target'],
                        labels=edge_row['labels'],
                        properties=edge_row['properties'],
                    )

                    # Determine the next node ID based on direction
                    next_id = edge_row['target']
                    if direction == 'incoming' or (
                        direction == 'both' and edge_row['target'] == node_id
                    ):
                        next_id = edge_row['source']

                    # Skip if it's the current node
                    if next_id == node_id:
                        continue

                    # Recursively traverse
                    await traverse_recursive(next_id, current_depth + 1, edge)

                    # Check if limit reached
                    if len(results) >= limit:
                        return

        await traverse_recursive(start_node)
        LOGGER.debug(
            'Traverse results: %s items, visited %s nodes',
            len(results),
            len(visited_nodes),
        )
        return results

    @staticmethod
    def _build_statement(
        select: str,
        labels: list[str] | None = None,
        properties: dict | None = None,
    ) -> tuple[sql.Composable, dict[str, typing.Any]]:
        """Generate the SQL for get_edges and get_nodes"""
        parameters: dict[str, typing.Any] = {}
        statement: list[str | sql.Composable] = [
            sql.SQL(select) + sql.SQL(' ')  # type: ignore
        ]
        if not labels and not properties:
            return sql.Composed(statement), parameters
        where: list[sql.Composable] = []
        if labels:
            parameters['labels'] = labels
            where.append(
                sql.SQL('labels') + sql.SQL(' && ') + sql.Placeholder('labels')
            )
        if properties:
            props = []
            for key, value in properties.items():
                props.append(
                    sql.SQL(f"properties->>'{key}'")  # type: ignore
                    + sql.SQL(' = ')
                    + sql.Placeholder(f'props_{key}')
                )
                parameters[f'props_{key}'] = str(value)
            if len(props) > 1:
                where.append(
                    sql.SQL('(') + sql.SQL(' OR ').join(props) + sql.SQL(')')
                )
            else:
                where.append(props[0])
        if where:
            statement.append(sql.SQL('WHERE '))
            statement.append(sql.SQL(' AND ').join(where))
        return sql.Composed(statement), parameters

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

    async def _add_embeddings(self, node_id: uuid.UUID, content: str) -> None:
        """Chunk the content and write the embeddings"""
        for offset, value in enumerate(self._embeddings.get(content)):
            async with self._postgres.callproc(
                'pgraf.add_embedding',
                {'node': node_id, 'chunk': offset, 'value': value},
            ) as cursor:
                result: dict[str, bool] = await cursor.fetchone()  # type: ignore
                if not result['success']:
                    raise errors.DatabaseError('Failed to insert embedding')
