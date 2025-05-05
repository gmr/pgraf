from importlib import metadata

from pgraf.errors import DatabaseError
from pgraf.graph import PGraf
from pgraf.models import ContentNode, Edge, Node, SearchResult

version = metadata.version('pgraf')

NodeTypes = Node | ContentNode | SearchResult

__all__ = [
    'ContentNode',
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
