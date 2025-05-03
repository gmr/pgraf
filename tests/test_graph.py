import uuid

from pgraf import graph, models, postgres
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

    async def test_lifecycle(self) -> None:
        node = await self.graph.add_node('test', {'label': 'test'})
        self.assertIsInstance(node, models.Node)
        self.assertEqual(node.type, 'test')
        self.assertDictEqual(node.properties, {'label': 'test'})

        value = await self.graph.get_node(node.id)
        self.assertIsNotNone(value)
        if value:  # Added type guard for mypy
            self.assertEqual(value.id, node.id)
            self.assertEqual(value.type, node.type)

            value.type = 'different'
            result = await self.graph.update_node(value)
            self.assertEqual(result.type, value.type)

            deleted = await self.graph.delete_node(value.id)
            self.assertTrue(deleted)

            result = await self.graph.get_node(value.id)
            self.assertIsNone(result)

    async def test_content_node_lifecycle(self) -> None:
        # Create a content node
        content_node = await self.graph.add_content_node(
            title='Test Content',
            content='This is test content',
            mimetype='text/plain',
            source='test',
            url='https://example.com',
            properties={'tag': 'test'},
        )
        self.assertIsInstance(content_node, models.ContentNode)
        self.assertEqual(content_node.type, 'content')
        self.assertEqual(content_node.title, 'Test Content')
        self.assertEqual(content_node.content, 'This is test content')
        self.assertEqual(content_node.url, 'https://example.com')
        self.assertEqual(content_node.source, 'test')
        self.assertEqual(content_node.mimetype, 'text/plain')
        self.assertDictEqual(content_node.properties, {'tag': 'test'})

        # Get the content node
        retrieved = await self.graph.get_node(content_node.id)
        self.assertIsNotNone(retrieved)
        self.assertIsInstance(retrieved, models.ContentNode)
        self.assertEqual(retrieved.id, content_node.id)
        self.assertEqual(retrieved.title, content_node.title)

        # Update the content node
        content_node.title = 'Updated Title'
        content_node.mimetype = 'text/html'
        result = await self.graph.update_content_node(content_node)
        self.assertEqual(result.title, 'Updated Title')
        self.assertEqual(result.mimetype, 'text/html')

        # Delete the content node
        deleted = await self.graph.delete_node(content_node.id)
        self.assertTrue(deleted)

        # Verify it's gone
        result = await self.graph.get_node(content_node.id)
        self.assertIsNone(result)

    async def test_get_nodes(self) -> None:
        data = common.load_test_data('test-content-nodes.yaml')
        nodes = []
        for value in data['values']:
            nodes.append(await self.graph.add_node('test', {'label': 'test'}))
            nodes.append(
                await self.graph.add_content_node(
                    title=str(uuid.uuid4()),
                    content=value,
                    mimetype='text/plain',
                    source='test',
                    url='https://example.com',
                    properties={'label': 'test'},
                )
            )
        result = await self.graph.get_nodes(properties={'label': 'test'})
        self.assertEqual(len(result), len(data['values']) * 2)
        for node in result:
            if node.type == 'content':
                self.assertIsInstance(node, models.ContentNode)
            else:
                self.assertIsInstance(node, models.Node)

        result = await self.graph.get_nodes(properties={'label': 'foo'})
        self.assertEqual(len(result), 0)

        result = await self.graph.get_nodes(
            properties={'label': 'test'}, node_types=['test']
        )
        self.assertEqual(len(result), len(data['values']))
        for node in result:
            self.assertIsInstance(node, models.Node)
            self.assertEqual(node.type, 'test')

        result = await self.graph.get_nodes(
            properties={'label': 'test'}, node_types=['content']
        )
        self.assertEqual(len(result), len(data['values']))
        for node in result:
            self.assertIsInstance(node, models.Node)
            self.assertEqual(node.type, 'content')
