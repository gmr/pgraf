import datetime
import typing
import uuid

import orjson
import pydantic

from pgraf import utils


class _ModelWithProperties(pydantic.BaseModel):
    """Base model to auto serialize/deserialize the jsonb field in Postgres"""

    created_at: datetime.datetime = pydantic.Field(
        default_factory=utils.current_timestamp
    )
    modified_at: datetime.datetime | None = None
    properties: dict[str, typing.Any] = pydantic.Field(
        default_factory=lambda: {}
    )

    @pydantic.model_validator(mode='before')
    @classmethod
    def deserialize_properties(cls, data):
        if isinstance(data, dict) and 'properties' in data:
            props = data['properties']
            if isinstance(props, str):
                try:
                    data['properties'] = orjson.loads(props)
                except orjson.JSONDecodeError:
                    pass
        return data

    @pydantic.field_serializer('properties')
    def serialize_properties(self, properties: dict[str, typing.Any]) -> str:
        return orjson.dumps(properties).decode('utf-8')


class Node(_ModelWithProperties):
    """A node represents an entity or object within the graph model."""

    id: uuid.UUID = pydantic.Field(default_factory=utils.uuidv7)
    type: str


class Edge(_ModelWithProperties):
    """An edge represents the relationship between two nodes"""

    source: uuid.UUID
    target: uuid.UUID
    label: str


class Embedding(pydantic.BaseModel):
    """An embedding is a fixed-length vector of floating-point numbers that
    represents the semantic meaning of a document chunk in a high-dimensional
    space, enabling similarity search operations for retrieving contextually
    relevant information in RAG systems."""

    node: uuid.UUID
    chunk: int
    value: list[float]

    @pydantic.field_validator('value')
    @classmethod
    def validate_value_length(cls, value: list[float]) -> list[float]:
        """Validate that the embedding value has exactly 384 dimensions."""
        if len(value) != 384:
            raise ValueError(
                f'Value must have exactly 384 dimensions, got {len(value)}'
            )
        return value


class ContentNode(Node):
    """Provides additional attributes for a content Node type"""

    type: str = 'content'
    title: str | None = None
    mimetype: str
    source: str
    content: str
    url: str | None = None


class SearchResult(ContentNode):
    """Used for the return results of a search"""

    similarity: float
