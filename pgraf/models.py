import datetime
import re
import typing
import uuid

import orjson
import pydantic

from pgraf import utils


class _ModelWithProperties(pydantic.BaseModel):
    """Base model to auto serialize/deserialize the jsonb field in Postgres"""

    properties: dict[str, typing.Any]

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
    created_at: datetime.datetime = pydantic.Field(
        default_factory=utils.current_timestamp
    )
    modified_at: datetime.datetime | None
    type: str


class Edge(_ModelWithProperties):
    """An edge represents the relationship between two nodes"""

    source: uuid.UUID
    target: uuid.UUID
    created_at: datetime.datetime = pydantic.Field(
        default_factory=utils.current_timestamp
    )
    modified_at: datetime.datetime | None
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
        """Validate that the embedding value has exactly 1536 dimensions."""
        if len(value) != 1536:
            raise ValueError(
                f'Value must have exactly 1536 dimensions, got {len(value)}'
            )
        return value


class TsPosition(pydantic.BaseModel):
    position: int
    weight: str | None


class TsLexeme(pydantic.BaseModel):
    positions: list[TsPosition]


class TsVector(pydantic.BaseModel):
    lexemes: dict[str, list[TsPosition]] = pydantic.Field(default_factory=dict)

    @pydantic.field_validator('lexemes', mode='before')
    @classmethod
    def parse_tsvector(cls, value):
        if isinstance(value, str):
            result = {}
            for match in re.finditer(
                r"'([^']+)':(\d+[A-D]?(?:,\d+[A-D]?)*)", value
            ):  # Match each lexeme entry: 'word':positions
                word, positions_str = match.groups()
                positions = []
                for pos_match in positions_str.split(','):
                    if pos_match[-1] in 'ABCD':
                        pos, weight = int(pos_match[:-1]), pos_match[-1]
                    else:
                        pos, weight = int(pos_match), None
                    positions.append(TsPosition(position=pos, weight=weight))
                result[word] = positions
            return result
        return value

    def __str__(self):
        parts = []
        for word, positions in self.lexemes.items():
            pos_strs = []
            for pos in positions:
                if pos.weight:
                    pos_strs.append(f'{pos.position}{pos.weight}')
                else:
                    pos_strs.append(f'{pos.position}')
            parts.append(f"'{word}':{','.join(pos_strs)}")
        return ' '.join(parts)


class DocumentNode(pydantic.BaseModel):
    """Provides additional attributes for a document Node type"""

    node: uuid.UUID
    title: str
    content: str
    type: str | None
    url: str | None
    vector: str | None = None

    model_config = {'json_schema_extra': {'exclude': ['vector']}}
