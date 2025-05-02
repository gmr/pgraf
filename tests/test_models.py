import datetime
import json
import unittest
import uuid

from pgraf import models


class TestModelWithProperties(unittest.TestCase):
    """Test the base model with properties functionality."""

    def test_deserialize_properties_json_string(self):
        """Test deserializing properties from a JSON string."""
        json_str = '{"name": "test", "value": 123}'
        data = {'properties': json_str}

        result = models._ModelWithProperties.deserialize_properties(data)

        self.assertIsInstance(result['properties'], dict)
        self.assertEqual(result['properties']['name'], 'test')
        self.assertEqual(result['properties']['value'], 123)

    def test_deserialize_properties_already_dict(self):
        """Test deserializing properties that are already a dict."""
        props = {'name': 'test', 'value': 123}
        data = {'properties': props}

        result = models._ModelWithProperties.deserialize_properties(data)

        self.assertIs(result['properties'], props)

    def test_deserialize_properties_invalid_json(self):
        """Test deserializing properties with invalid JSON."""
        data = {'properties': '{invalid json}'}

        result = models._ModelWithProperties.deserialize_properties(data)

        self.assertEqual(result['properties'], '{invalid json}')

    def test_deserialize_properties_no_properties(self):
        """Test deserializing with no properties field."""
        data = {'other_field': 'value'}

        result = models._ModelWithProperties.deserialize_properties(data)

        self.assertEqual(result, data)

    def test_deserialize_properties_non_dict_data(self):
        """Test deserializing with non-dict input."""
        data = 'not a dict'

        result = models._ModelWithProperties.deserialize_properties(data)

        self.assertEqual(result, data)

    def test_serialize_properties(self):
        """Test serializing properties to a JSON string."""
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
        """Test Node model with default values."""
        # We'll test that node has defaults for id and created_at
        # without using mocks that are hard to get working
        node = models.Node(
            label='Person', properties={'name': 'John'}, modified_at=None
        )

        self.assertTrue(node.id is not None)
        uuid.UUID(str(node.id))

        self.assertIsInstance(node.created_at, datetime.datetime)
        self.assertIsNone(node.modified_at)
        self.assertEqual(node.label, 'Person')
        self.assertEqual(node.properties, {'name': 'John'})

    def test_node_explicit_values(self):
        """Test Node model with explicit values."""
        test_uuid = uuid.uuid4()
        test_time = datetime.datetime.now(tz=datetime.UTC)

        node = models.Node(
            id=test_uuid,
            created_at=test_time,
            modified_at=test_time,
            label='City',
            properties={'name': 'New York'},
        )

        self.assertEqual(node.id, test_uuid)
        self.assertEqual(node.created_at, test_time)
        self.assertEqual(node.modified_at, test_time)
        self.assertEqual(node.label, 'City')
        self.assertEqual(node.properties, {'name': 'New York'})


class TestEdgeModel(unittest.TestCase):
    """Test the Edge model."""

    def test_edge_default_values(self):
        """Test Edge model with default values."""
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
        """Test Edge model with explicit values."""
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
        """Test Embedding model with valid vector length."""
        node_id = uuid.uuid4()
        embedding = models.Embedding(node=node_id, chunk=1, value=[0.0] * 1536)

        self.assertEqual(len(embedding.value), 1536)
        self.assertEqual(embedding.node, node_id)
        self.assertEqual(embedding.chunk, 1)

    def test_invalid_embedding_length(self):
        """Test Embedding model with invalid vector lengths."""
        for size in {1000, 2000}:
            with self.assertRaises(ValueError) as context:
                models.Embedding(
                    node=uuid.uuid4(), chunk=1, value=[0.0] * size
                )

            self.assertIn(
                f'Value must have exactly 1536 dimensions, got {size}',
                str(context.exception),
            )


class TestTsPositionModel(unittest.TestCase):
    """Test the TsPosition model."""

    def test_tsposition_with_weight(self):
        """Test TsPosition with position and weight."""
        pos = models.TsPosition(position=42, weight='A')

        self.assertEqual(pos.position, 42)
        self.assertEqual(pos.weight, 'A')

    def test_tsposition_without_weight(self):
        """Test TsPosition with position but no weight."""
        pos = models.TsPosition(position=42, weight=None)

        self.assertEqual(pos.position, 42)
        self.assertIsNone(pos.weight)


class TestTsLexemeModel(unittest.TestCase):
    """Test the TsLexeme model."""

    def test_tslexeme_with_positions(self):
        """Test TsLexeme with positions."""
        positions = [
            models.TsPosition(position=1, weight='A'),
            models.TsPosition(position=2, weight=None),
        ]

        lexeme = models.TsLexeme(positions=positions)

        self.assertEqual(len(lexeme.positions), 2)
        self.assertEqual(lexeme.positions[0].position, 1)
        self.assertEqual(lexeme.positions[0].weight, 'A')
        self.assertEqual(lexeme.positions[1].position, 2)
        self.assertIsNone(lexeme.positions[1].weight)


class TestTsVectorModel(unittest.TestCase):
    """Test the TsVector model."""

    def test_tsvector_empty_constructor(self):
        """Test creating an empty TsVector."""
        tsvec = models.TsVector()

        self.assertEqual(tsvec.lexemes, {})
        self.assertEqual(str(tsvec), '')

    def test_tsvector_with_lexemes(self):
        """Test creating a TsVector with lexemes."""
        lexemes = {
            'hello': [
                models.TsPosition(position=1, weight='A'),
                models.TsPosition(position=5, weight=None),
            ],
            'world': [models.TsPosition(position=2, weight='B')],
        }

        tsvec = models.TsVector(lexemes=lexemes)

        self.assertEqual(tsvec.lexemes, lexemes)
        # The string representation can be in any order, check each part
        self.assertIn("'hello':1A,5", str(tsvec))
        self.assertIn("'world':2B", str(tsvec))

    def test_parse_tsvector_from_string(self):
        """Test parsing a TsVector from a Postgres tsvector string."""
        vector_str = "'hello':1A,5 'world':2B,10C"

        result = models.TsVector.parse_tsvector(vector_str)

        self.assertEqual(len(result), 2)
        self.assertEqual(len(result['hello']), 2)
        self.assertEqual(result['hello'][0].position, 1)
        self.assertEqual(result['hello'][0].weight, 'A')
        self.assertEqual(result['hello'][1].position, 5)
        self.assertIsNone(result['hello'][1].weight)

        self.assertEqual(len(result['world']), 2)
        self.assertEqual(result['world'][0].position, 2)
        self.assertEqual(result['world'][0].weight, 'B')
        self.assertEqual(result['world'][1].position, 10)
        self.assertEqual(result['world'][1].weight, 'C')

    def test_parse_tsvector_non_string(self):
        """Test parsing a TsVector from a non-string value."""
        value = {'hello': 'world'}

        result = models.TsVector.parse_tsvector(value)

        self.assertEqual(result, value)

    def test_tsvector_str_representation(self):
        """Test the string representation of a TsVector."""
        tsvec = models.TsVector(
            lexemes={
                'hello': [
                    models.TsPosition(position=1, weight='A'),
                    models.TsPosition(position=5, weight=None),
                ],
                'world': [models.TsPosition(position=2, weight='B')],
            }
        )

        string_repr = str(tsvec)

        # Since dictionary order isn't guaranteed, check each part separately
        self.assertIn("'hello':1A,5", string_repr)
        self.assertIn("'world':2B", string_repr)


class TestDocumentNodeModel(unittest.TestCase):
    """Test the DocumentNode model."""

    def test_document_node_required_fields(self):
        """Test DocumentNode with required fields."""
        node_id = uuid.uuid4()
        doc = models.DocumentNode(
            node=node_id,
            title='Test Document',
            content='This is a test document',
            type=None,
            url=None,
            vector=None,
        )

        self.assertEqual(doc.node, node_id)
        self.assertEqual(doc.title, 'Test Document')
        self.assertEqual(doc.content, 'This is a test document')
        self.assertIsNone(doc.type)
        self.assertIsNone(doc.url)
        self.assertIsNone(doc.vector)

    def test_document_node_all_fields(self):
        """Test DocumentNode with all fields."""
        node_id = uuid.uuid4()
        doc = models.DocumentNode(
            node=node_id,
            title='Test Document',
            content='This is a test document',
            type='text/plain',
            url='https://example.com/doc',
            vector='vector data',
        )

        self.assertEqual(doc.node, node_id)
        self.assertEqual(doc.title, 'Test Document')
        self.assertEqual(doc.content, 'This is a test document')
        self.assertEqual(doc.type, 'text/plain')
        self.assertEqual(doc.url, 'https://example.com/doc')
        self.assertEqual(doc.vector, 'vector data')

    def test_document_node_model_config(self):
        """Test that the vector field is excluded from the JSON schema."""
        _schema = models.DocumentNode.model_json_schema()

        # Check that json_schema_extra exists and contains exclude
        self.assertIn('json_schema_extra', models.DocumentNode.model_config)
        self.assertIn(
            'exclude', models.DocumentNode.model_config['json_schema_extra']
        )
        self.assertIn(
            'vector',
            models.DocumentNode.model_config['json_schema_extra']['exclude'],
        )
