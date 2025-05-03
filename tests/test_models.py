import datetime
import json
import unittest
import uuid

from pgraf import models


class TestModelWithProperties(unittest.TestCase):
    """Test the base model with properties functionality."""

    def test_deserialize_properties_json_string(self):
        json_str = '{"name": "test", "value": 123}'
        data = {'properties': json_str}

        result = models._ModelWithProperties.deserialize_properties(data)

        self.assertIsInstance(result['properties'], dict)
        self.assertEqual(result['properties']['name'], 'test')
        self.assertEqual(result['properties']['value'], 123)

    def test_deserialize_properties_already_dict(self):
        props = {'name': 'test', 'value': 123}
        data = {'properties': props}

        result = models._ModelWithProperties.deserialize_properties(data)

        self.assertIs(result['properties'], props)

    def test_deserialize_properties_invalid_json(self):
        data = {'properties': '{invalid json}'}

        result = models._ModelWithProperties.deserialize_properties(data)

        self.assertEqual(result['properties'], '{invalid json}')

    def test_deserialize_properties_no_properties(self):
        data = {'other_field': 'value'}

        result = models._ModelWithProperties.deserialize_properties(data)

        self.assertEqual(result, data)

    def test_deserialize_properties_non_dict_data(self):
        data = 'not a dict'

        result = models._ModelWithProperties.deserialize_properties(data)

        self.assertEqual(result, data)

    def test_serialize_properties(self):
        props = {'name': 'test', 'value': 123}
        model = models._ModelWithProperties(properties=props)

        result = model.serialize_properties(props)

        self.assertIsInstance(result, str)
        # Deserialize the JSON string to verify its contents
        deserialized = json.loads(result)
        self.assertEqual(deserialized, props)


class TestNodeModel(unittest.TestCase):
    """Test the Node model."""

    def test_node_default_values(self):
        # We'll test that node has defaults for id and created_at
        # without using mocks that are hard to get working
        node = models.Node(
            type='Person', properties={'name': 'John'}, modified_at=None
        )

        self.assertTrue(node.id is not None)
        uuid.UUID(str(node.id))

        self.assertIsInstance(node.created_at, datetime.datetime)
        self.assertIsNone(node.modified_at)
        self.assertEqual(node.type, 'Person')
        self.assertEqual(node.properties, {'name': 'John'})

    def test_node_explicit_values(self):
        test_uuid = uuid.uuid4()
        test_time = datetime.datetime.now(tz=datetime.UTC)

        node = models.Node(
            id=test_uuid,
            created_at=test_time,
            modified_at=test_time,
            type='City',
            properties={'name': 'New York'},
        )

        self.assertEqual(node.id, test_uuid)
        self.assertEqual(node.created_at, test_time)
        self.assertEqual(node.modified_at, test_time)
        self.assertEqual(node.type, 'City')
        self.assertEqual(node.properties, {'name': 'New York'})


class TestEdgeModel(unittest.TestCase):
    """Test the Edge model."""

    def test_edge_default_values(self):
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()

        edge = models.Edge(
            source=source_id,
            target=target_id,
            label='KNOWS',
            properties={'since': 2023},
            modified_at=None,
        )

        self.assertEqual(edge.source, source_id)
        self.assertEqual(edge.target, target_id)
        self.assertIsInstance(edge.created_at, datetime.datetime)
        self.assertIsNone(edge.modified_at)
        self.assertEqual(edge.label, 'KNOWS')
        self.assertEqual(edge.properties, {'since': 2023})

    def test_edge_explicit_values(self):
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()
        test_time = datetime.datetime.now(tz=datetime.UTC)

        edge = models.Edge(
            source=source_id,
            target=target_id,
            created_at=test_time,
            modified_at=test_time,
            label='LIVES_IN',
            properties={'since': 2020},
        )

        self.assertEqual(edge.source, source_id)
        self.assertEqual(edge.target, target_id)
        self.assertEqual(edge.created_at, test_time)
        self.assertEqual(edge.modified_at, test_time)
        self.assertEqual(edge.label, 'LIVES_IN')
        self.assertEqual(edge.properties, {'since': 2020})


class TestEmbeddingModel(unittest.TestCase):
    """Test the Embedding model."""

    def test_valid_embedding_length(self):
        node_id = uuid.uuid4()
        embedding = models.Embedding(node=node_id, chunk=1, value=[0.0] * 384)

        self.assertEqual(len(embedding.value), 384)
        self.assertEqual(embedding.node, node_id)
        self.assertEqual(embedding.chunk, 1)

    def test_invalid_embedding_length(self):
        for size in {1000, 2000}:
            with self.assertRaises(ValueError) as context:
                models.Embedding(
                    node=uuid.uuid4(), chunk=1, value=[0.0] * size
                )
            self.assertIn(
                f'Value must have exactly 384 dimensions, got {size}',
                str(context.exception),
            )


class TestContentNodeModel(unittest.TestCase):
    """Test the ContentNode model."""

    def test_content_node_required_fields(self):
        node_id = uuid.uuid4()
        doc = models.ContentNode(
            id=node_id,
            title='Test Document',
            content='This is a test document',
            url=None,
            source='test',
            mimetype='text/plain',
        )
        self.assertEqual(doc.id, node_id)
        self.assertEqual(doc.title, 'Test Document')
        self.assertEqual(doc.content, 'This is a test document')
        self.assertEqual(doc.type, 'content')
        self.assertIsNone(doc.url)
        self.assertEqual(doc.source, 'test')
        self.assertEqual(doc.mimetype, 'text/plain')

    def test_content_node_all_fields(self):
        node_id = uuid.uuid4()
        doc = models.ContentNode(
            id=node_id,
            title='Test Document',
            content='This is a test document',
            url='https://example.com/doc',
            source='web',
            mimetype='text/html',
            properties={'label': 'test'},
        )
        self.assertEqual(doc.id, node_id)
        self.assertEqual(doc.title, 'Test Document')
        self.assertEqual(doc.content, 'This is a test document')
        self.assertEqual(doc.type, 'content')
        self.assertEqual(doc.url, 'https://example.com/doc')
        self.assertEqual(doc.source, 'web')
        self.assertEqual(doc.mimetype, 'text/html')
        self.assertDictEqual(doc.properties, {'label': 'test'})
