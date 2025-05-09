import re

import numpy
import sentence_transformers

DEFAULT_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+')


class Embeddings:
    """Handles the generation of vector embeddings for text content.

    This class provides functionality to convert text into vector embeddings
    using sentence transformers. It handles chunking of text to ensure
    optimal embedding generation.

    Args:
        model: The sentence transformer model to use for embeddings
    """

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        """Initialize the embeddings generator with the specified model.

        Args:
            model: The sentence transformer model to use
                (defaults to 'all-MiniLM-L6-v2')
        """
        self.transformer = sentence_transformers.SentenceTransformer(model)

    def get(self, value: str) -> list[numpy.ndarray]:
        """Generate embeddings for the provided text value.

        The text is automatically chunked into manageable pieces
        using sentence boundaries and maximum word count.

        Args:
            value: The text to generate embeddings for

        Returns:
            A list of numpy arrays containing the embeddings for each chunk
        """
        embeddings: list[numpy.ndarray] = []
        for chunk in self._chunk_text(value):
            result: numpy.ndarray = self.transformer.encode(
                chunk, convert_to_numpy=True, convert_to_tensor=False
            )
            embeddings.append(result)
        return embeddings

    @staticmethod
    def _chunk_text(text: str, max_words: int = 256) -> list[str]:
        """Split text into chunks of sentences with a maximum word count."""
        if not text.strip():
            return []

        sentences = SENTENCE_PATTERN.split(text)
        word_counts = [len(sentence.split()) for sentence in sentences]
        chunks: list[str] = []
        current: list[str] = []
        cwc = 0
        for i, sentence in enumerate(sentences):
            word_count = word_counts[i]
            if cwc + word_count > max_words and cwc > 0:
                chunks.append(' '.join(current))
                current, cwc = [], 0
            current.append(sentence)
            cwc += word_count

        if current:
            chunks.append(' '.join(current))
        return chunks
