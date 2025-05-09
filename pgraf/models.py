import datetime
import typing
import uuid

import orjson
import pydantic

from pgraf import utils


class _GraphModel(pydantic.BaseModel):
    """Base model to auto serialize/deserialize the jsonb field in Postgres.

    This is the base class for all graph models (Node, Edge) in pgraf.
    It provides common fields and functionality for serialization and
    deserialization.

    Attributes:
        created_at: Timestamp when the model was created
        modified_at: Timestamp when the model was last modified
        properties: Dictionary of arbitrary properties associated with
        the model
        labels: List of labels for categorizing the model
    """

    created_at: datetime.datetime = pydantic.Field(
        default_factory=utils.current_timestamp,
        description='Timestamp when the model was created',
    )
    modified_at: datetime.datetime | None = pydantic.Field(
        default=None, description='Timestamp when the model was last modified'
    )
    properties: dict[str, typing.Any] = pydantic.Field(
        default_factory=lambda: {},
        description='Dictionary of arbitrary properties for the model',
    )
    labels: list[str] = pydantic.Field(
        default_factory=list,
        description='List of labels for categorizing the model',
    )

    @property
    def latest_timestamp(self) -> datetime.datetime:
        if self.modified_at is not None:
            return self.modified_at
        return self.created_at

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


class Node(_GraphModel):
    """A node represents an entity or object within the graph model."""

    id: uuid.UUID = pydantic.Field(default_factory=utils.uuidv7)
    mimetype: str | None = None
    content: str | None = None


class Edge(_GraphModel):
    """An edge represents the relationship between two nodes"""

    source: uuid.UUID
    target: uuid.UUID


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


class SearchResult(Node):
    """Used for the return results of a search"""

    similarity: float
