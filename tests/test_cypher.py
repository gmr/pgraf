import unittest

from psycopg import sql

from pgraf import cypher


class CypherTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.cypher = cypher.CypherParser()

    def test_parse_match_return(self) -> None:
        """Test parsing a simple MATCH...RETURN query"""
        query = """
        MATCH (p:Product)-[:CATEGORY]->(l:ProductCategory)
        RETURN p.name
        """
        result = self.cypher.parse(query)
        self.assertIsInstance(result, sql.Composed)

        # Instead of converting to string, check the components
        # to verify the query structure is correct
        sql_components = result._obj

        select_clause = False
        from_clause = False
        join_clause = False
        properties_access = False

        for component in sql_components:
            component_str = str(component)
            if 'SELECT' in component_str:
                select_clause = True
            if 'FROM pgraf.nodes' in component_str:
                from_clause = True
            if 'JOIN pgraf.edges' in component_str:
                join_clause = True
            if 'properties->>' in component_str:
                properties_access = True

        self.assertTrue(select_clause, 'SELECT clause not found in query')
        self.assertTrue(from_clause, 'FROM clause not found in query')
        self.assertTrue(join_clause, 'JOIN clause not found in query')
        self.assertTrue(
            properties_access, 'Properties access not found in query'
        )

    def test_parse_match_where_return(self) -> None:
        """Test parsing a MATCH...WHERE...RETURN query"""
        query = """
        MATCH (p:Person)
        WHERE p.age > 30
        RETURN p.name, p.age
        """
        result = self.cypher.parse(query)
        self.assertIsInstance(result, sql.Composed)

        # Instead of converting to string, check the components
        # to verify the query structure is correct
        sql_components = result._obj

        select_clause = False
        from_clause = False
        where_clause = False

        for component in sql_components:
            component_str = str(component)
            if 'SELECT' in component_str:
                select_clause = True
            if 'FROM pgraf.nodes' in component_str:
                from_clause = True
            if 'WHERE' in component_str:
                where_clause = True

        self.assertTrue(select_clause, 'SELECT clause not found in query')
        self.assertTrue(from_clause, 'FROM clause not found in query')
        self.assertTrue(where_clause, 'WHERE clause not found in query')

    def test_parse_match_multiple_relationships(self) -> None:
        """Test parsing a query with multiple relationship patterns"""
        query = """
        MATCH (p:Person)-[:FRIEND]->(f:Person)-[:LIVES_IN]->(c:City)
        RETURN p.name, f.name, c.name
        """
        result = self.cypher.parse(query)
        self.assertIsInstance(result, sql.Composed)

        # Instead of converting to string, check the components
        # to verify the query structure is correct
        sql_components = result._obj

        join_edges_count = 0
        join_nodes_count = 0

        for component in sql_components:
            component_str = str(component)
            if 'JOIN pgraf.edges' in component_str:
                join_edges_count += 1
            if 'JOIN pgraf.nodes' in component_str:
                join_nodes_count += 1

        # We should have at least 2 edge joins for the two relationships
        self.assertGreaterEqual(
            join_edges_count, 2, 'Not enough edge JOINs found'
        )
        # We should have at least 1 node join
        self.assertGreaterEqual(
            join_nodes_count, 1, 'Not enough node JOINs found'
        )
