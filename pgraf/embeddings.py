import enum
import re
import typing

import numpy
import openai
import sentence_transformers

DEFAULT_HUGGING_FACE_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
DEFAULT_OPENAI_MODEL = 'text-embedding-3-small'
SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+')


class Engine(enum.Enum):
    """Enum for the available embedding engines"""

    HUGGING_FACE = 'hugging-face'
    OPENAI = 'openai'


class Embeddings:
    def __init__(
        self,
        engine=Engine.HUGGING_FACE,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        if engine == Engine.HUGGING_FACE:
            self._engine: HuggingFace | OpenAI = HuggingFace(model)
        elif engine == Engine.OPENAI:
            self._engine = OpenAI(model, api_key)
        else:
            raise ValueError(f'Invalid engine: {engine}')

    def __getattr__(self, item: str) -> typing.Any:
        return getattr(self._engine, item)


class OpenAI:
    """Handles the generation of vector embeddings for text content using the
    OpenAI client
    """

    def __init__(
        self,
        model: str | None = DEFAULT_OPENAI_MODEL,
        api_key: str | None = None,
    ) -> None:
        """Initialize the embeddings generator with the specified model."""
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model or DEFAULT_OPENAI_MODEL

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
        for chunk in _chunk_text(value):
            response = self.client.embeddings.create(
                input=chunk, model=self.model
            )
            embeddings.append(numpy.array(response.data[0].embedding))
        return embeddings


class HuggingFace:
    """Handles the generation of vector embeddings for text content.

    This class provides functionality to convert text into vector embeddings
    using sentence transformers. It handles chunking of text to ensure
    optimal embedding generation.

    Args:
        model: The sentence transformer model to use for embeddings
    """

    def __init__(self, model: str | None = DEFAULT_HUGGING_FACE_MODEL) -> None:
        """Initialize the embeddings generator with the specified model.

        Args:
            model: The sentence transformer model to use
                (defaults to 'all-MiniLM-L6-v2')
        """
        self.transformer = sentence_transformers.SentenceTransformer(
            model or DEFAULT_HUGGING_FACE_MODEL
        )

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
        for chunk in _chunk_text(value):
            result: numpy.ndarray = self.transformer.encode(
                chunk, convert_to_numpy=True, convert_to_tensor=False
            )
            embeddings.append(result)
        return embeddings


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
