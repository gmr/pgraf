import unittest
import unittest.mock

import numpy

from pgraf import embeddings
from tests import common


class TestEmbeddings(unittest.TestCase):
    embeddings: embeddings.Embeddings

    @classmethod
    def setUpClass(cls) -> None:
        cls.embeddings = embeddings.Embeddings(
            engine=embeddings.Engine.HUGGING_FACE
        )

    def test_chunk_text_empty(self) -> None:
        result = embeddings._chunk_text('')
        self.assertEqual(result, [])

    def test_chunk_text_single_sentence(self) -> None:
        text = 'This is a single sentence with fewer than 256 words.'
        result = embeddings._chunk_text(text)
        self.assertEqual(result, [text])

    def test_chunk_text_multiple_sentences(self) -> None:
        text = (
            'This is the first sentence. This is the second sentence. '
            'This is the third sentence.'
        )
        result = embeddings._chunk_text(text)
        self.assertEqual(result, [text])

    def test_chunk_text_exceeds_limit(self) -> None:
        sentence = ' '.join(['word'] * 50) + '.'
        text = ' '.join([sentence] * 6)
        result = embeddings._chunk_text(text)
        self.assertEqual(len(result), 2)
        first_chunk_words = len(result[0].split())
        self.assertLessEqual(first_chunk_words, 256)
        second_chunk_words = len(result[1].split())
        self.assertLessEqual(second_chunk_words, 256)

    def test_chunk_text_custom_limit(self) -> None:
        sentence = ' '.join(['word'] * 20) + '.'
        text = ' '.join([sentence] * 5)
        result = embeddings._chunk_text(text, max_words=50)
        self.assertEqual(len(result), 3)
        for chunk in result:
            chunk_words = len(chunk.split())
            self.assertLessEqual(chunk_words, 50)

    def test_chunk_text_long_sentence(self) -> None:
        long_sentence = ' '.join(['word'] * 300)
        result = embeddings._chunk_text(long_sentence)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], long_sentence)

    def test_get_paragraph_hugging_face(self) -> None:
        data = common.load_test_data('test-embeddings.yaml')
        self.assertIsInstance(data, dict)
        result = self.embeddings.get(data['value'])
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], numpy.ndarray)
        self.assertEqual(len(result[0]), 384)

    def test_init_hugging_face_default_model(self) -> None:
        embed = embeddings.Embeddings(engine=embeddings.Engine.HUGGING_FACE)
        self.assertIsInstance(embed._engine, embeddings.HuggingFace)
        # Check that transformer is initialized
        if isinstance(embed._engine, embeddings.HuggingFace):
            self.assertIsNotNone(embed._engine.transformer)

    def test_init_hugging_face_custom_model(self) -> None:
        custom_model = 'sentence-transformers/all-MiniLM-L12-v2'
        embed = embeddings.Embeddings(
            engine=embeddings.Engine.HUGGING_FACE, model=custom_model
        )
        self.assertIsInstance(embed._engine, embeddings.HuggingFace)
        # Check that transformer is initialized
        if isinstance(embed._engine, embeddings.HuggingFace):
            self.assertIsNotNone(embed._engine.transformer)

    def test_init_invalid_engine(self) -> None:
        with self.assertRaises(ValueError) as context:
            embeddings.Embeddings(engine='invalid')
        self.assertIn('Invalid engine', str(context.exception))


class TestOpenAIEmbeddings(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_client = unittest.mock.Mock()
        self.mock_response = unittest.mock.Mock()
        self.mock_response.data = [unittest.mock.Mock()]
        self.mock_response.data[0].embedding = [0.1, 0.2, 0.3]
        self.mock_client.embeddings.create.return_value = self.mock_response

    @unittest.mock.patch('openai.OpenAI')
    def test_init_openai_default_model(
        self, mock_openai: unittest.mock.Mock
    ) -> None:
        mock_openai.return_value = self.mock_client
        embed = embeddings.Embeddings(engine=embeddings.Engine.OPENAI)
        self.assertIsInstance(embed._engine, embeddings.OpenAI)
        openai_engine = embed._engine
        self.assertIsInstance(openai_engine, embeddings.OpenAI)
        if isinstance(openai_engine, embeddings.OpenAI):
            self.assertEqual(
                openai_engine.model, embeddings.DEFAULT_OPENAI_MODEL
            )
        mock_openai.assert_called_once_with(api_key=None)

    @unittest.mock.patch('openai.OpenAI')
    def test_init_openai_custom_model_and_key(
        self, mock_openai: unittest.mock.Mock
    ) -> None:
        mock_openai.return_value = self.mock_client
        custom_model = 'text-embedding-3-large'
        api_key = 'test-api-key'
        embed = embeddings.Embeddings(
            engine=embeddings.Engine.OPENAI,
            model=custom_model,
            api_key=api_key,
        )
        self.assertIsInstance(embed._engine, embeddings.OpenAI)
        openai_engine = embed._engine
        self.assertIsInstance(openai_engine, embeddings.OpenAI)
        if isinstance(openai_engine, embeddings.OpenAI):
            self.assertEqual(openai_engine.model, custom_model)
        mock_openai.assert_called_once_with(api_key=api_key)

    @unittest.mock.patch('openai.OpenAI')
    def test_openai_get_single_chunk(
        self, mock_openai: unittest.mock.Mock
    ) -> None:
        mock_openai.return_value = self.mock_client
        embed = embeddings.Embeddings(engine=embeddings.Engine.OPENAI)

        text = 'This is a short text.'
        result = embed.get(text)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], numpy.ndarray)
        numpy.testing.assert_array_equal(
            result[0], numpy.array([0.1, 0.2, 0.3])
        )

        self.mock_client.embeddings.create.assert_called_once_with(
            input=text, model=embeddings.DEFAULT_OPENAI_MODEL
        )

    @unittest.mock.patch('openai.OpenAI')
    def test_openai_get_multiple_chunks(
        self, mock_openai: unittest.mock.Mock
    ) -> None:
        mock_openai.return_value = self.mock_client
        embed = embeddings.Embeddings(engine=embeddings.Engine.OPENAI)

        # Create text that will be chunked
        sentence = ' '.join(['word'] * 50) + '.'
        text = ' '.join(
            [sentence] * 6
        )  # 300 words total, should create 2 chunks

        result = embed.get(text)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        for chunk_result in result:
            self.assertIsInstance(chunk_result, numpy.ndarray)
            numpy.testing.assert_array_equal(
                chunk_result, numpy.array([0.1, 0.2, 0.3])
            )

        self.assertEqual(self.mock_client.embeddings.create.call_count, 2)

    @unittest.mock.patch('openai.OpenAI')
    def test_openai_get_empty_text(
        self, mock_openai: unittest.mock.Mock
    ) -> None:
        mock_openai.return_value = self.mock_client
        embed = embeddings.Embeddings(engine=embeddings.Engine.OPENAI)

        result = embed.get('')

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
        self.mock_client.embeddings.create.assert_not_called()

    @unittest.mock.patch('openai.OpenAI')
    def test_openai_get_with_custom_model(
        self, mock_openai: unittest.mock.Mock
    ) -> None:
        mock_openai.return_value = self.mock_client
        custom_model = 'text-embedding-3-large'
        embed = embeddings.Embeddings(
            engine=embeddings.Engine.OPENAI, model=custom_model
        )

        text = 'Test text'
        result = embed.get(text)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

        self.mock_client.embeddings.create.assert_called_once_with(
            input=text, model=custom_model
        )

    def test_openai_engine_direct_init_default(self) -> None:
        with unittest.mock.patch('openai.OpenAI') as mock_openai:
            mock_openai.return_value = self.mock_client
            engine = embeddings.OpenAI()

            self.assertEqual(engine.model, embeddings.DEFAULT_OPENAI_MODEL)
            mock_openai.assert_called_once_with(api_key=None)

    def test_openai_engine_direct_init_custom(self) -> None:
        with unittest.mock.patch('openai.OpenAI') as mock_openai:
            mock_openai.return_value = self.mock_client
            custom_model = 'text-embedding-3-large'
            api_key = 'test-key'

            engine = embeddings.OpenAI(model=custom_model, api_key=api_key)

            self.assertEqual(engine.model, custom_model)
            mock_openai.assert_called_once_with(api_key=api_key)

    def test_openai_engine_direct_get(self) -> None:
        with unittest.mock.patch('openai.OpenAI') as mock_openai:
            mock_openai.return_value = self.mock_client
            engine = embeddings.OpenAI()

            text = 'Direct test'
            result = engine.get(text)

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)
            self.assertIsInstance(result[0], numpy.ndarray)
            numpy.testing.assert_array_equal(
                result[0], numpy.array([0.1, 0.2, 0.3])
            )


class TestHuggingFaceEmbeddings(unittest.TestCase):
    def test_hugging_face_engine_direct_init_default(self) -> None:
        engine = embeddings.HuggingFace()
        # Check that transformer is initialized
        self.assertIsNotNone(engine.transformer)

    def test_hugging_face_engine_direct_init_custom(self) -> None:
        custom_model = 'sentence-transformers/all-MiniLM-L12-v2'
        engine = embeddings.HuggingFace(model=custom_model)
        # Check that transformer is initialized
        self.assertIsNotNone(engine.transformer)

    def test_hugging_face_engine_direct_get(self) -> None:
        engine = embeddings.HuggingFace()
        data = common.load_test_data('test-embeddings.yaml')
        self.assertIsInstance(data, dict)
        result = engine.get(data['value'])

        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], numpy.ndarray)
        self.assertEqual(len(result[0]), 384)
