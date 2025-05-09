# pgraf

[![PyPI version](https://badge.fury.io/py/pgraf.svg)](https://badge.fury.io/py/pgraf)
[![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://gmr.github.io/pgraf/)
[![Python Version](https://img.shields.io/pypi/pyversions/pgraf)](https://pypi.org/project/pgraf/)
[![License](https://img.shields.io/github/license/gmr/pgraf)](https://github.com/gmr/pgraf/blob/main/LICENSE)

pgraf turns PostgreSQL into a lightning fast property graph engine with vector search capabilities, designed for use in AI agents and applications.

## Features

- **Typed Models**: Strong typing with Pydantic models for nodes, edges, and content
- **Vector Search**: Built-in support for embeddings and semantic search
- **Property Graph**: Full property graph capabilities with typed nodes and labeled edges
- **Asynchronous API**: Modern async/await API for high-performance applications
- **PostgreSQL Backend**: Uses PostgreSQL's power for reliability and scalability

[**📚 Documentation**](https://gmr.github.io/pgraf/) | [**🚀 Quick Start**](https://gmr.github.io/pgraf/installation/) | [**📖 API Reference**](https://gmr.github.io/pgraf/api/graph/)

## Installation

### Prerequisites

- Python 3.12+
- PostgreSQL 14+ with [pgvector](https://github.com/pgvector/pgvector) extension installed

### Installing pgraf

```bash
# From PyPI
pip install pgraf

# From source
git clone https://github.com/gmr/pgraf.git
cd pgraf
pip install -e .
```

### Database Setup

1. Create a database:
   ```bash
   createdb pgraf
   ```

2. Apply the schema (includes pgvector extension creation):
   ```bash
   psql -d pgraf -f schema/pgraf.sql
   ```

The [schema file](schema/pgraf.sql) creates the pgvector extension, necessary tables, indexes, and stored procedures for the graph functionality.

## Usage

### Basic Example

```python
import asyncio
from pgraf import graph

async def main():
    # Initialize the graph with PostgreSQL connection
    pgraf = graph.PGraf(url="postgresql://postgres:postgres@localhost:5432/pgraf")

    try:
        # Add a simple node
        person = await pgraf.add_node(
            labels=["person"],
            properties={"name": "Alice", "age": 30}
        )

        # Add a node with content and vector embeddings
        document = await pgraf.add_node(
            labels=["document"],
            properties={
                "tags": ["example"],
                "title": "Sample Document",
                "url": "https://example.com"
            },
            mimetype="text/plain",
            content="This is a sample document that will be embedded in vector space."
        )

        # Create a relationship between nodes
        await pgraf.add_edge(
            source=person.id,
            target=document.id,
            labels=["CREATED"],
            properties={"timestamp": "2023-01-01"}
        )

        # Retrieve nodes
        all_people = []
        async for node in pgraf.get_nodes(
            labels=["person"],
            properties={"name": "Alice"}
        ):
            all_people.append(node)

        # Traverse the graph
        traversal_results = await pgraf.traverse(
            start_node=person.id,
            edge_labels=["CREATED"],
            direction="outgoing",
            max_depth=2
        )

        # Print traversal results
        for node, edge in traversal_results:
            print(f"Node: {node.labels[0] if node.labels else 'Unknown'} {node.id}")
            if edge:
                print(f"  via edge: {edge.labels[0] if edge.labels else 'Unknown'}")

    finally:
        await pgraf.aclose()


if __name__ == "__main__":
    asyncio.run(main())
```

### Semantic Search Example

```python
import asyncio
from pgraf import graph, models
from sentence_transformers import SentenceTransformer

async def main():
    # Initialize the graph
    pgraf = graph.PGraf(url="postgresql://postgres:postgres@localhost:5432/pgraf")

    try:
        # Add some documents with content for vector embedding
        await pgraf.add_node(
            labels=["document"],
            properties={"title": "Climate Change Overview"},
            content="Climate change is the long-term alteration of temperature and weather patterns.",
            mimetype="text/plain"
        )

        await pgraf.add_node(
            labels=["document"],
            properties={"title": "Machine Learning Basics"},
            content="Machine learning is a branch of AI focused on building models that learn from data.",
            mimetype="text/plain"
        )

        await pgraf.add_node(
            labels=["document"],
            properties={"title": "Graph Databases"},
            content="Graph databases store data in nodes and edges, representing entities and relationships.",
            mimetype="text/plain"
        )

        # No need to explicitly generate embeddings - they're created
        # automatically when nodes with content are added

        # Perform semantic search
        # This automatically generates an embedding for the query text
        results = await pgraf.search(
            query="How do databases represent connections between data points?",
            labels=["document"],
            limit=2
        )

        # Print results sorted by relevance
        for result in results:
            print(f"Match: {result.properties.get('title')} (Score: {result.similarity:.4f})")
            print(f"Content: {result.content[:100]}...")
            print()

        # For custom queries, the search method automatically converts query to embeddings
        # You just need to provide the query text, and it will use the internal embedding model
        query_text = "AI techniques for data analysis"

        # The search method handles embedding generation internally
        custom_results = await pgraf.search(
            query=query_text,
            labels=["document"],
            similarity_threshold=0.3,  # Adjust similarity threshold as needed
            limit=2
        )

        for result in custom_results:
            print(f"Custom search match: {result.properties.get('title')} (Score: {result.similarity:.4f})")

    finally:
        await pgraf.aclose()

if __name__ == "__main__":
    asyncio.run(main())
```

## Requirements

- Python 3.12+
- PostgreSQL 14+

## License

See [LICENSE](LICENSE) for details.
