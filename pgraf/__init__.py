from importlib import metadata

from pgraf.errors import DatabaseError
from pgraf.graph import PGraf
from pgraf.models import Edge, Node, SearchResult

version = metadata.version('pgraf')

NodeTypes = Node | SearchResult

__all__ = [
    'DatabaseError',
    'Edge',
    'Node',
    'NodeTypes',
    'PGraf',
    'SearchResult',
    'errors',
    'models',
    'version',
]
