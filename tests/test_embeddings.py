import pathlib
import unittest

import yaml

from pgraf import embeddings

DATA_DIR = pathlib.Path(__file__).parent / 'data'


class TestEmbeddings(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.embeddings = embeddings.Embeddings()

    def test_chunk_text_empty(self) -> None:
        result = self.embeddings._chunk_text('')
        self.assertEqual(result, [])

    def test_chunk_text_single_sentence(self) -> None:
        text = 'This is a single sentence with fewer than 256 words.'
        result = self.embeddings._chunk_text(text)
        self.assertEqual(result, [text])

    def test_chunk_text_multiple_sentences(self) -> None:
        text = (
            'This is the first sentence. This is the second sentence. '
            'This is the third sentence.'
        )
        result = self.embeddings._chunk_text(text)
        self.assertEqual(result, [text])

    def test_chunk_text_exceeds_limit(self) -> None:
        sentence = ' '.join(['word'] * 50) + '.'
        text = ' '.join([sentence] * 6)
        result = self.embeddings._chunk_text(text)
        self.assertEqual(len(result), 2)
        first_chunk_words = len(result[0].split())
        self.assertLessEqual(first_chunk_words, 256)
        second_chunk_words = len(result[1].split())
        self.assertLessEqual(second_chunk_words, 256)

    def test_chunk_text_custom_limit(self) -> None:
        sentence = ' '.join(['word'] * 20) + '.'
        text = ' '.join([sentence] * 5)
        result = self.embeddings._chunk_text(text, max_words=50)
        self.assertEqual(len(result), 3)
        for chunk in result:
            chunk_words = len(chunk.split())
            self.assertLessEqual(chunk_words, 50)

    def test_chunk_text_long_sentence(self) -> None:
        long_sentence = ' '.join(['word'] * 300)
        result = self.embeddings._chunk_text(long_sentence)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], long_sentence)

    def test_get_paragrpah(self) -> None:
        with (DATA_DIR / 'test-embeddings.yaml').open('r') as handle:
            data = yaml.safe_load(handle)
        result = self.embeddings.get(data['value'])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result[0]), 384)
        self.assertEqual(result, data['expectation'])
