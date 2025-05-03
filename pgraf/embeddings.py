import re

import sentence_transformers

DEFAULT_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+')


class Embeddings:
    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.transformer = sentence_transformers.SentenceTransformer(model)

    def get(self, value: str) -> list[list[float]]:
        """Get embeddings for value passed in"""
        embeddings = []
        for chunk in self._chunk_text(value):
            result = self.transformer.encode(chunk)
            embeddings.append([float(vector) for vector in result])
        return embeddings

    @staticmethod
    def _chunk_text(text: str, max_words: int = 256) -> list[str]:
        """Split text into chunks of sentences with a maximum word count."""
        if not text.strip():
            return []

        sentences = SENTENCE_PATTERN.split(text)
        word_counts = [len(sentence.split()) for sentence in sentences]
        chunks, current, cwc = [], [], 0
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
