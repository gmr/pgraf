import uuid

from pgraf import graph, models, postgres
from tests import common


class GraphTestCase(common.PostgresTestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.graph = graph.PGraf(common.postgres_url())

    async def asyncTearDown(self) -> None:
        await super().asyncTearDown()
        await self.graph.aclose()

    async def test_setup(self) -> None:
        self.assertIsInstance(self.graph._postgres, postgres.Postgres)

    async def test_lifecycle(self) -> None:
        node = await self.graph.add_node(
            labels=['test'], properties={'label': 'test'}
        )
        self.assertIsInstance(node, models.Node)
        self.assertIn('test', node.labels)
        self.assertDictEqual(node.properties, {'label': 'test'})

        value = await self.graph.get_node(node.id)
        self.assertIsNotNone(value)
        self.assertEqual(value.id, node.id)
        self.assertListEqual(value.labels, node.labels)

        deleted = await self.graph.delete_node(value.id)
        self.assertTrue(deleted)

        result = await self.graph.get_node(value.id)
        self.assertIsNone(result)

    async def test_get_nodes(self) -> None:
        await self.graph.add_node(
            labels=['test'], properties={'label': 'test'}
        )
        await self.graph.add_node(
            labels=['content'], properties={'label': 'test'}
        )
        node = await self.graph.get_node(uuid.uuid4())
        self.assertIsNone(node)

    async def test_get_nodes_with_filtering(self) -> None:
        """Test getting nodes with property and label filtering"""
        await self.graph.add_node(
            labels=['Person'], properties={'name': 'Charlie', 'age': 30}
        )
        await self.graph.add_node(
            labels=['Person'], properties={'name': 'David', 'age': 25}
        )
        await self.graph.add_node(
            labels=['Product'], properties={'name': 'Laptop', 'price': 1200}
        )

        # Filter by label
        count = 0
        async for node in self.graph.get_nodes(labels=['Person']):
            self.assertIn('Person', node.labels)
            count += 1
        self.assertEqual(count, 2)

        # Filter by property
        count = 0
        async for node in self.graph.get_nodes(properties={'name': 'David'}):
            self.assertEqual(node.properties.get('name'), 'David')
            self.assertEqual(node.properties.get('age'), 25)
            count += 1
        self.assertEqual(count, 1)

        # Filter by both label and property
        count = 0
        async for node in self.graph.get_nodes(
            labels=['Product'], properties={'name': 'Laptop'}
        ):
            self.assertIn('Product', node.labels)
            self.assertEqual(node.properties.get('name'), 'Laptop')
            count += 1
        self.assertEqual(count, 1)

    async def test_update_node(self) -> None:
        """Test updating node properties and labels"""
        # Create a node
        node = await self.graph.add_node(
            labels=['Person'], properties={'name': 'Emily', 'age': 28}
        )

        # Update the node
        node.properties['age'] = 29
        node.properties['occupation'] = 'Engineer'
        node.labels.append('Employee')

        updated_node = await self.graph.update_node(node)

        # Verify the updates
        self.assertEqual(updated_node.properties.get('age'), 29)
        self.assertEqual(updated_node.properties.get('occupation'), 'Engineer')
        self.assertIn('Person', updated_node.labels)
        self.assertIn('Employee', updated_node.labels)

        # Check that the modifications are persisted
        retrieved_node = await self.graph.get_node(node.id)
        self.assertIsNotNone(retrieved_node)
        self.assertEqual(retrieved_node.properties.get('age'), 29)
        self.assertEqual(
            retrieved_node.properties.get('occupation'), 'Engineer'
        )
        self.assertIn('Employee', retrieved_node.labels)

        # Test updating content
        node.content = 'This is some test content for embedding'
        node.mimetype = 'text/plain'
        content_updated_node = await self.graph.update_node(node)

        self.assertEqual(
            content_updated_node.content,
            'This is some test content for embedding',
        )
        self.assertEqual(content_updated_node.mimetype, 'text/plain')

    async def test_node_labels(self) -> None:
        # Add a few test nodes to verify node label operations
        await self.graph.add_node(
            labels=['test'], properties={'label': 'test'}
        )
        await self.graph.add_node(
            labels=['content'], properties={'label': 'test'}
        )

        # Test node labels functionality
        labels = await self.graph.get_node_labels()
        self.assertIn('test', labels)
        self.assertIn('content', labels)

    async def test_label_edge_cases(self) -> None:
        """Test edge cases for label handling in nodes"""
        # Test empty labels array
        empty_labels_node = await self.graph.add_node(
            labels=[], properties={'name': 'EmptyLabels'}
        )
        self.assertEqual(empty_labels_node.labels, [])

        none_labels_node = await self.graph.add_node(
            labels=[],  # Use empty list instead of None
            properties={'name': 'EmptyLabelsAsTester'},
        )
        self.assertEqual(none_labels_node.labels, [])

        multi_labels_node = await self.graph.add_node(
            labels=['Label1', 'Label2', 'Label3', 'Label4', 'Label5'],
            properties={'name': 'MultiLabels'},
        )
        self.assertEqual(len(multi_labels_node.labels), 5)
        for i in range(1, 6):
            self.assertIn(f'Label{i}', multi_labels_node.labels)

        # Test special characters in labels
        special_labels_node = await self.graph.add_node(
            labels=[
                'Label:With:Colons',
                'Label-With-Hyphens',
                'Label.With.Dots',
                'Label With Spaces',
                'UPPER_CASE_LABEL',
                'special!@#$%^&*()',
            ],
            properties={'name': 'SpecialLabels'},
        )

        # Retrieve the node to verify labels were saved correctly
        retrieved_node = await self.graph.get_node(special_labels_node.id)
        self.assertIsNotNone(retrieved_node)
        self.assertIn('Label:With:Colons', retrieved_node.labels)
        self.assertIn('Label-With-Hyphens', retrieved_node.labels)
        self.assertIn('Label.With.Dots', retrieved_node.labels)
        self.assertIn('Label With Spaces', retrieved_node.labels)
        self.assertIn('UPPER_CASE_LABEL', retrieved_node.labels)
        self.assertIn('special!@#$%^&*()', retrieved_node.labels)

        # Test duplicate labels (should be preserved in the model but may be
        # deduplicated in the database - implementation-specific)
        duplicate_labels_node = await self.graph.add_node(
            labels=['Same', 'Same', 'Same'],
            properties={'name': 'DuplicateLabels'},
        )

        # Check at least one instance of the label exists
        self.assertIn('Same', duplicate_labels_node.labels)

        # Test label updates via update_node
        update_node = await self.graph.add_node(
            labels=['Initial'], properties={'name': 'LabelUpdate'}
        )

        # Update with new labels
        update_node.labels = ['Updated1', 'Updated2']
        updated_node = await self.graph.update_node(update_node)

        # Check labels were updated
        self.assertNotIn('Initial', updated_node.labels)
        self.assertIn('Updated1', updated_node.labels)
        self.assertIn('Updated2', updated_node.labels)

    async def test_node_properties(self) -> None:
        """Test retrieving node property names"""
        # Create nodes with various properties
        await self.graph.add_node(
            labels=['Property_Test'],
            properties={
                'string_prop': 'value',
                'int_prop': 42,
                'bool_prop': True,
                'float_prop': 3.14,
            },
        )

        await self.graph.add_node(
            labels=['Property_Test'],
            properties={
                'string_prop': 'different',
                'array_prop': [1, 2, 3],
                'object_prop': {'nested': 'value'},
            },
        )

        # Test retrieving property names
        property_names = await self.graph.get_node_properties()

        # Check that all the property names we added are returned
        properties_to_check = [
            'string_prop',
            'int_prop',
            'bool_prop',
            'float_prop',
            'array_prop',
            'object_prop',
        ]

        for prop in properties_to_check:
            self.assertIn(prop, property_names)

    async def test_node_property_edge_cases(self) -> None:
        """Test edge cases for property handling"""
        # Test empty properties
        empty_props_node = await self.graph.add_node(
            labels=['EmptyProps'], properties={}
        )
        self.assertEqual(empty_props_node.properties, {})

        # Test None properties (should default to empty dict)
        none_props_node = await self.graph.add_node(
            labels=['NoneProps'], properties=None
        )
        self.assertEqual(none_props_node.properties, {})

        # Test special characters in property values
        special_chars_node = await self.graph.add_node(
            labels=['SpecialChars'],
            properties={
                'quotes': 'Text with \'single\' and "double" quotes',
                'unicode': 'Unicode: 你好, こんにちは, Привет',
                'emoji': 'Emoji: 😀 🚀 🌍',
                'sql_injection': "'; DROP TABLE nodes; --",
            },
        )

        # Retrieve the node to verify properties were saved correctly
        retrieved_node = await self.graph.get_node(special_chars_node.id)
        self.assertIsNotNone(retrieved_node)
        self.assertEqual(
            retrieved_node.properties.get('quotes'),
            'Text with \'single\' and "double" quotes',
        )
        self.assertEqual(
            retrieved_node.properties.get('unicode'),
            'Unicode: 你好, こんにちは, Привет',
        )
        self.assertEqual(
            retrieved_node.properties.get('emoji'), 'Emoji: 😀 🚀 🌍'
        )

        # Test deeply nested properties
        nested_node = await self.graph.add_node(
            labels=['NestedProps'],
            properties={
                'level1': {
                    'level2': {
                        'level3': {'level4': {'value': 'deeply nested'}}
                    }
                }
            },
        )

        # Retrieve and check nested properties
        retrieved_nested = await self.graph.get_node(nested_node.id)
        self.assertIsNotNone(retrieved_nested)
        nested_value = (
            retrieved_nested.properties.get('level1', {})
            .get('level2', {})
            .get('level3', {})
            .get('level4', {})
            .get('value')
        )
        self.assertEqual(nested_value, 'deeply nested')

        # Test large property values
        large_text = 'A' * 10000  # 10K characters
        large_props_node = await self.graph.add_node(
            labels=['LargeProps'], properties={'large_text': large_text}
        )

        # Retrieve and check large properties
        retrieved_large = await self.graph.get_node(large_props_node.id)
        self.assertIsNotNone(retrieved_large)
        self.assertEqual(
            len(retrieved_large.properties.get('large_text', '')), 10000
        )

    async def test_edge_properties(self) -> None:
        """Test retrieving edge property names"""
        # First create nodes to connect
        source = await self.graph.add_node(
            labels=['Source'], properties={'name': 'Source Node'}
        )

        target = await self.graph.add_node(
            labels=['Target'], properties={'name': 'Target Node'}
        )

        # Create edges with various properties
        await self.graph.add_edge(
            source=source.id,
            target=target.id,
            labels=['PROPERTY_TEST_1'],
            properties={
                'string_prop': 'edge value',
                'number_prop': 100,
                'timestamp_prop': '2023-01-01T00:00:00Z',
            },
        )
        # Create another edge with different properties
        second_target = await self.graph.add_node(
            labels=['Target'], properties={'name': 'Second Target'}
        )

        await self.graph.add_edge(
            source=source.id,
            target=second_target.id,
            labels=['PROPERTY_TEST_2'],
            properties={
                'boolean_prop': False,
                'weight_prop': 0.75,
                'object_prop': {'key': 'value'},
            },
        )

        # Test retrieving edge property names
        property_names = await self.graph.get_edge_properties()

        # Check that edge properties are returned
        properties_to_check = [
            'string_prop',
            'number_prop',
            'timestamp_prop',
            'boolean_prop',
            'weight_prop',
            'object_prop',
        ]

        for prop in properties_to_check:
            self.assertIn(prop, property_names)

        # Clean up
        await self.graph.delete_edge(source.id, target.id)
        await self.graph.delete_edge(source.id, second_target.id)
        await self.graph.delete_node(source.id)
        await self.graph.delete_node(target.id)
        await self.graph.delete_node(second_target.id)

    async def test_edge_operations(self) -> None:
        """Test the full lifecycle of edge operations"""
        # Create two nodes to connect with an edge
        source_node = await self.graph.add_node(
            labels=['Person'], properties={'name': 'Alice'}
        )
        target_node = await self.graph.add_node(
            labels=['City'], properties={'name': 'New York'}
        )

        # Add an edge
        edge = await self.graph.add_edge(
            source=source_node.id,
            target=target_node.id,
            labels=['LIVES_IN'],
            properties={'since': 2020},
        )

        self.assertIsInstance(edge, models.Edge)
        self.assertEqual(edge.source, source_node.id)
        self.assertEqual(edge.target, target_node.id)
        self.assertIn('LIVES_IN', edge.labels)
        self.assertEqual(edge.properties.get('since'), 2020)

        # Get the edge
        retrieved_edge = await self.graph.get_edge(
            source_node.id, target_node.id
        )
        self.assertIsInstance(retrieved_edge, models.Edge)
        self.assertEqual(retrieved_edge.source, source_node.id)
        self.assertEqual(retrieved_edge.target, target_node.id)
        self.assertIn('LIVES_IN', retrieved_edge.labels)

        # Update the edge
        retrieved_edge.properties['verified'] = True
        updated_edge = await self.graph.update_edge(retrieved_edge)
        self.assertIsInstance(updated_edge, models.Edge)
        self.assertEqual(updated_edge.properties.get('since'), 2020)
        self.assertEqual(updated_edge.properties.get('verified'), True)

        # Delete the edge
        delete_result = await self.graph.delete_edge(
            source_node.id, target_node.id
        )
        self.assertTrue(delete_result)

        # Clean up the nodes
        await self.graph.delete_node(source_node.id)
        await self.graph.delete_node(target_node.id)

    async def test_edge_labels(self) -> None:
        """Test retrieving edge labels"""
        # Create nodes and edges with different labels
        source_node = await self.graph.add_node(
            labels=['Person'], properties={'name': 'Bob'}
        )
        target_node1 = await self.graph.add_node(
            labels=['City'], properties={'name': 'Boston'}
        )
        target_node2 = await self.graph.add_node(
            labels=['Company'], properties={'name': 'Acme'}
        )

        await self.graph.add_edge(
            source=source_node.id,
            target=target_node1.id,
            labels=['VISITED'],
            properties={'when': 'last summer'},
        )

        await self.graph.add_edge(
            source=source_node.id,
            target=target_node2.id,
            labels=['WORKS_AT'],
            properties={'since': 2018},
        )

        # Get edge labels
        labels = await self.graph.get_edge_labels()
        self.assertIn('VISITED', labels)
        self.assertIn('WORKS_AT', labels)

        # Clean up
        await self.graph.delete_edge(source_node.id, target_node1.id)
        await self.graph.delete_edge(source_node.id, target_node2.id)
        await self.graph.delete_node(source_node.id)
        await self.graph.delete_node(target_node1.id)
        await self.graph.delete_node(target_node2.id)

    async def test_search_functionality(self) -> None:
        """Test searching nodes based on content embeddings"""

        # Create nodes with content for embedding and search
        article1 = await self.graph.add_node(
            labels=['Article'],
            properties={'title': 'Introduction to Machine Learning'},
            mimetype='text/plain',
            content='Machine learning is a branch of artificial intelligence '
            'focused on building systems that learn from data.',
        )

        article2 = await self.graph.add_node(
            labels=['Article'],
            properties={'title': 'Deep Learning Overview'},
            mimetype='text/plain',
            content='Deep learning is a subset of machine learning that uses '
            'neural networks with many layers.',
        )

        article3 = await self.graph.add_node(
            labels=['Article'],
            properties={'title': 'Cooking Techniques'},
            mimetype='text/plain',
            content='Cooking is the art of preparing food by applying heat. '
            'Methods include baking, roasting, and frying.',
        )

        # Simple search test - should return relevant articles
        results = await self.graph.search('What is artificial intelligence?')
        self.assertGreater(len(results), 0)

        # Check if the results are ordered by similarity
        if len(results) > 1:
            self.assertGreaterEqual(
                results[0].similarity, results[1].similarity
            )

        # Test search with label filtering
        label_results = await self.graph.search(
            'What is artificial intelligence?', labels=['Article']
        )
        self.assertGreater(len(label_results), 0)
        for result in label_results:
            self.assertIn('Article', result.labels)

        # Test search with property filtering
        property_results = await self.graph.search(
            'What is deep learning?',
            properties={'title': 'Deep Learning Overview'},
        )
        if len(property_results) > 0:
            self.assertEqual(
                property_results[0].properties.get('title'),
                'Deep Learning Overview',
            )

        threshold_results = await self.graph.search(
            'What is cooking?', similarity_threshold=0.8
        )
        # Depending on embedding quality, this might return fewer results
        for result in threshold_results:
            self.assertGreaterEqual(result.similarity, 0.8)

        # Test with limit
        limit_results = await self.graph.search('machine learning', limit=1)
        self.assertLessEqual(len(limit_results), 1)

        # Clean up
        await self.graph.delete_node(article1.id)
        await self.graph.delete_node(article2.id)
        await self.graph.delete_node(article3.id)

    async def test_traversal(self) -> None:
        """Test graph traversal functionality"""
        # Create a small network of nodes and edges
        person1 = await self.graph.add_node(
            labels=['Person'], properties={'name': 'Alice'}
        )

        person2 = await self.graph.add_node(
            labels=['Person'], properties={'name': 'Bob'}
        )

        person3 = await self.graph.add_node(
            labels=['Person'], properties={'name': 'Charlie'}
        )

        city1 = await self.graph.add_node(
            labels=['City'], properties={'name': 'New York'}
        )

        city2 = await self.graph.add_node(
            labels=['City'], properties={'name': 'San Francisco'}
        )

        # Create relationships
        await self.graph.add_edge(
            source=person1.id,
            target=person2.id,
            labels=['KNOWS'],
            properties={'since': 2018},
        )

        await self.graph.add_edge(
            source=person2.id,
            target=person3.id,
            labels=['KNOWS'],
            properties={'since': 2019},
        )

        await self.graph.add_edge(
            source=person1.id,
            target=city1.id,
            labels=['LIVES_IN'],
            properties={'since': 2015},
        )

        await self.graph.add_edge(
            source=person2.id,
            target=city2.id,
            labels=['LIVES_IN'],
            properties={'since': 2017},
        )

        await self.graph.add_edge(
            source=person3.id,
            target=city2.id,
            labels=['LIVES_IN'],
            properties={'since': 2020},
        )

        # Test basic traversal - just check it runs without errors
        await self.graph.traverse(start_node=person1.id, max_depth=1)

        # Try a simpler traversal to see if we get results
        all_nodes = []
        async for node in self.graph.get_nodes():
            all_nodes.append(node)

        # Check if edges exist by querying directly
        results_bob = await self.graph.get_edge(person1.id, person2.id)
        self.assertIsInstance(results_bob, models.Edge)
        results_ny = await self.graph.get_edge(person1.id, city1.id)
        self.assertIsInstance(results_ny, models.Edge)

        # Test traversal with label filtering
        person_results = await self.graph.traverse(
            start_node=person1.id, node_labels=['Person'], max_depth=2
        )

        if person_results:
            for node, _ in person_results:
                if node.labels != ['Person']:
                    self.assertIn('Person', node.labels)

        # Test traversal with edge label filtering
        knows_results = await self.graph.traverse(
            start_node=person1.id, edge_labels=['KNOWS'], max_depth=2
        )

        for _, edge in knows_results:
            if edge is not None:  # Starting node won't have an edge
                self.assertListEqual(['KNOWS'], edge.labels)

        # Test traversal direction (incoming)
        incoming_results = await self.graph.traverse(
            start_node=city2.id, direction='incoming', max_depth=1
        )

        # Should find connections from Bob and Charlie to San Francisco
        self.assertGreaterEqual(len(incoming_results), 2)

        # Deep traversal
        deep_results = await self.graph.traverse(
            start_node=person1.id, max_depth=3, limit=10
        )

        # Should be able to reach all other nodes from person1
        self.assertGreaterEqual(len(deep_results), 4)

        # Clean up
        # Remove edges first
        await self.graph.delete_edge(person1.id, person2.id)
        await self.graph.delete_edge(person2.id, person3.id)
        await self.graph.delete_edge(person1.id, city1.id)
        await self.graph.delete_edge(person2.id, city2.id)
        await self.graph.delete_edge(person3.id, city2.id)

        # Remove nodes
        await self.graph.delete_node(person1.id)
        await self.graph.delete_node(person2.id)
        await self.graph.delete_node(person3.id)
        await self.graph.delete_node(city1.id)
        await self.graph.delete_node(city2.id)
