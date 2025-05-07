import logging
import re
import uuid

import antlr4
import antlr4_cypher
from psycopg import sql

LOGGER = logging.getLogger(__name__)


class CypherParser:
    """
    Parser for Cypher query language that translates to PostgreSQL.

    This implementation supports basic MATCH-RETURN queries with:
    - Node patterns with labels
    - Relationship patterns with types
    - Property access
    - Simple WHERE clauses

    The implementation is based on regex parsing for simplicity while the full
    ANTLR4 visitor-based implementation can be developed incrementally.

    """

    def __init__(self) -> None:
        """Initialize the Cypher parser."""
        self._node_pattern = re.compile(
            r'\((\w+)?(?::(\w+))?\s*(?:{([^}]*)})?\)'
        )
        self._rel_pattern = re.compile(
            r'\[(\w+)?(?::(\w+))?\s*(?:{([^}]*)})?]'
        )
        self._prop_pattern = re.compile(r'(\w+)\.(\w+)')
        self._split_pattern = re.compile(r'(-\[.*?]->|<-\[.*?]-)')

    def parse(self, query: str) -> sql.Composable:
        """
        Parse a Cypher query and translate it to a PostgreSQL query.

        Args:
            query: The Cypher query string

        Returns:
            A SQL Composable object representing the equivalent PostgreSQL
            query
        """
        # Remove comments and normalize whitespace
        query = self._preprocess_query(query)

        # Extract the key clauses
        match_clause = self._extract_clause(
            query, r'MATCH\s+(.*?)(?:WHERE|RETURN|$)'
        )
        where_clause = self._extract_clause(
            query, r'WHERE\s+(.*?)(?:RETURN|$)'
        )
        return_clause = self._extract_clause(query, r'RETURN\s+(.*?)(?:$)')

        if not match_clause:
            raise ValueError('MATCH clause is required')

        if not return_clause:
            raise ValueError('RETURN clause is required')

        # Parse the pattern
        nodes, relationships = self._parse_pattern(match_clause)

        # Generate the SQL
        return self._generate_sql(
            nodes, relationships, where_clause, return_clause
        )

    @staticmethod
    def _preprocess_query(query: str) -> str:
        """Preprocess the query by removing comments & normalizing whitespace.

        Args:
            query: The Cypher query string

        Returns:
            The preprocessed query string
        """
        # Remove comments
        query = re.sub(r'//.*?$', '', query, flags=re.MULTILINE)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)

        # Normalize whitespace
        query = re.sub(r'\s+', ' ', query).strip()

        return query

    @staticmethod
    def _extract_clause(query: str, pattern: str) -> str:
        """Extract a clause from the query.

        Args:
            query: The Cypher query string
            pattern: The regex pattern to extract the clause

        Returns:
            The extracted clause or an empty string if not found
        """
        match = re.search(pattern, query, re.IGNORECASE)
        return match.group(1).strip() if match else ''

    def _parse_pattern(
        self, pattern: str
    ) -> tuple[dict[str, dict], list[dict]]:
        """
        Parse a Cypher pattern into nodes and relationships.

        Args:
            pattern: The Cypher pattern string

        Returns:
            A tuple containing a dictionary of nodes & a list of relationships
        """
        nodes = {}
        relationships = []

        # Split the pattern into node and relationship segments
        segments = self._split_pattern.split(pattern)

        current_node = None
        for i, segment in enumerate(segments):
            segment = segment.strip()
            if not segment:
                continue

            if segment.startswith('-') or segment.startswith('<'):
                rel_match = self._rel_pattern.search(segment)
                if rel_match:
                    var_name, rel_type, props_str = rel_match.groups()

                    # Determine direction
                    direction = 'out'
                    if segment.startswith('<'):
                        direction = 'in'

                    # Parse properties
                    properties = {}
                    if props_str:
                        for prop in props_str.split(','):
                            if ':' in prop:
                                key, value = prop.split(':', 1)
                                properties[key.strip()] = value.strip()

                    # Add the relationship
                    if current_node is not None and i + 1 < len(segments):
                        next_node = self._parse_node(segments[i + 1])
                        if next_node:
                            rel_id = str(uuid.uuid4())
                            rel = {
                                'id': rel_id,
                                'variable': var_name,
                                'type': rel_type,
                                'properties': properties,
                                'direction': direction,
                                'source': current_node['variable'],
                                'target': next_node['variable'],
                            }
                            relationships.append(rel)

                            # Update node aliases
                            if next_node['variable'] not in nodes:
                                nodes[next_node['variable']] = next_node

            else:
                node = self._parse_node(segment)
                if node:
                    current_node = node
                    if node['variable'] not in nodes:
                        nodes[node['variable']] = node

        return nodes, relationships

    def _parse_node(self, node_str: str) -> dict | None:
        """
        Parse a node pattern.

        Args:
            node_str: The node pattern string

        Returns:
            A dictionary representing the node, or None if parsing fails
        """
        node_match = self._node_pattern.search(node_str)
        if not node_match:
            return None

        var_name, label, props_str = node_match.groups()

        # Generate a placeholder variable name if none provided
        if not var_name:
            var_name = f'anon_{str(uuid.uuid4())[:8]}'

        # Parse properties
        properties = {}
        if props_str:
            for prop in props_str.split(','):
                if ':' in prop:
                    key, value = prop.split(':', 1)
                    properties[key.strip()] = value.strip()

        return {'variable': var_name, 'label': label, 'properties': properties}

    def _generate_sql(
        self,
        nodes: dict[str, dict],
        relationships: list[dict],
        where_clause: str,
        return_clause: str,
    ) -> sql.Composed:
        """
        Generate a SQL query from the parsed Cypher elements.

        Args:
            nodes: A dictionary of node variables to node information
            relationships: A list of relationship information
            where_clause: The WHERE clause of the Cypher query
            return_clause: The RETURN clause of the Cypher query

        Returns:
            A SQL Composable object representing the PostgreSQL query
        """
        # Build the SELECT clause
        select_clause = [sql.SQL('SELECT ')]

        # Process the RETURN clause
        return_items = []
        for item in return_clause.split(','):
            item = item.strip()
            if '.' in item:
                # Property access
                prop_match = self._prop_pattern.match(item)
                if prop_match:
                    var_name, prop_name = prop_match.groups()
                    if var_name in nodes:
                        return_items.append(
                            sql.SQL('{}.properties->>{}').format(
                                sql.Identifier(var_name),
                                sql.Literal(prop_name),
                            )
                        )
            elif item in nodes:
                # Whole node return
                return_items.append(
                    sql.SQL('{}.*').format(sql.Identifier(item))
                )
            elif item == '*':
                # Return everything
                for node_var in nodes:
                    return_items.append(
                        sql.SQL('{}.*').format(sql.Identifier(node_var))
                    )

        if return_items:
            select_clause.append(sql.SQL(', ').join(return_items))
        else:
            # Default to all nodes
            for node_var in nodes:
                return_items.append(
                    sql.SQL('{}.*').format(sql.Identifier(node_var))
                )
            select_clause.append(sql.SQL(', ').join(return_items))

        # Build the FROM clause
        from_clause = []
        join_clauses = []

        # Add the first node to the FROM clause
        first_node = next(iter(nodes.values()))
        first_node_var = first_node['variable']

        from_clause.append(
            sql.SQL(' FROM pgraf.nodes AS {}').format(
                sql.Identifier(first_node_var)
            )
        )

        # Add label condition if present
        where_conditions = []
        if first_node['label']:
            where_conditions.append(
                sql.SQL('{}.type = {}').format(
                    sql.Identifier(first_node_var),
                    sql.Literal(first_node['label']),
                )
            )

        # Add property conditions for the first node
        if first_node['properties']:
            for key, value in first_node['properties'].items():
                # Handle quoted strings
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                where_conditions.append(
                    sql.SQL('{}.properties->>{}={}').format(
                        sql.Identifier(first_node_var),
                        sql.Literal(key),
                        sql.Literal(value),
                    )
                )

        # Add the remaining nodes and relationships as JOINs
        for rel in relationships:
            source_var = rel['source']
            target_var = rel['target']
            rel_var = (
                rel['variable']
                if rel['variable']
                else f'r_{source_var}_{target_var}'
            )

            # Add join for the relationship
            join_clauses.append(
                sql.SQL(' JOIN pgraf.edges AS {} ON ').format(
                    sql.Identifier(rel_var)
                )
            )

            # Add the relationship condition based on direction
            if rel['direction'] == 'out':
                join_clauses.append(
                    sql.SQL('({}.id = {}.source AND').format(
                        sql.Identifier(source_var), sql.Identifier(rel_var)
                    )
                )
            else:  # in
                join_clauses.append(
                    sql.SQL('({}.id = {}.target AND').format(
                        sql.Identifier(source_var), sql.Identifier(rel_var)
                    )
                )

            # Add relationship type condition if present
            if rel['type']:
                join_clauses.append(
                    sql.SQL(' {}.label = {} AND').format(
                        sql.Identifier(rel_var), sql.Literal(rel['type'])
                    )
                )

            # Add the closing part of the relationship condition
            if rel['direction'] == 'out':
                join_clauses.append(
                    sql.SQL(' {}.target = {}.id)').format(
                        sql.Identifier(rel_var), sql.Identifier(target_var)
                    )
                )
            else:  # in
                join_clauses.append(
                    sql.SQL(' {}.source = {}.id)').format(
                        sql.Identifier(rel_var), sql.Identifier(target_var)
                    )
                )

            # Add JOIN for the target node if it's not the first node
            if target_var != first_node_var:
                # Always add the node join
                join_clauses.append(
                    sql.SQL(' JOIN pgraf.nodes AS {} ON TRUE').format(
                        sql.Identifier(target_var)
                    )
                )

                # Add label condition for the target node
                target_node = nodes[target_var]
                if target_node['label']:
                    where_conditions.append(
                        sql.SQL('{}.type = {}').format(
                            sql.Identifier(target_var),
                            sql.Literal(target_node['label']),
                        )
                    )

                # Add property conditions for the target node
                if target_node['properties']:
                    for key, value in target_node['properties'].items():
                        # Handle quoted strings
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        where_conditions.append(
                            sql.SQL('{}.properties->>{}={}').format(
                                sql.Identifier(target_var),
                                sql.Literal(key),
                                sql.Literal(value),
                            )
                        )

        # Process the WHERE clause
        if where_clause:
            # Simple property comparison (e.g., n.prop > value)
            prop_match = re.search(
                r'(\w+)\.(\w+)\s*([=><!]=?)\s*([^,\s]+)', where_clause
            )
            if prop_match:
                var_name, prop_name, operator, value = prop_match.groups()

                # Handle quoted strings
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]

                if var_name in nodes:
                    where_conditions.append(
                        sql.SQL('({}.properties->>{}) {} {}').format(
                            sql.Identifier(var_name),
                            sql.Literal(prop_name),
                            sql.SQL(operator),
                            sql.Literal(value),
                        )
                    )

        # Build the WHERE clause if there are conditions
        where_clause = []
        if where_conditions:
            where_clause.append(sql.SQL(' WHERE '))
            where_clause.append(sql.SQL(' AND ').join(where_conditions))

        # Combine all parts
        query_parts = []
        query_parts.extend(select_clause)
        query_parts.extend(from_clause)
        query_parts.extend(join_clauses)
        query_parts.extend(where_clause)

        return sql.Composed(query_parts)

    @staticmethod
    def _get_parser(query: str) -> antlr4_cypher.CypherParser:
        """
        Get a Cypher parser instance for the given query.

        Args:
            query: The Cypher query string

        Returns:
            A Cypher parser instance
        """
        lexer = antlr4_cypher.CypherLexer(antlr4.InputStream(query))
        token_stream = antlr4.CommonTokenStream(lexer)
        return antlr4_cypher.CypherParser(token_stream)
