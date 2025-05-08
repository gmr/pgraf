# pgraf

pgraf turns PostgreSQL into a lightning fast property graph engine with vector search capabilities, designed for use in AI agents and applications.

## Features

- **Typed Models**: Strong typing with Pydantic models for nodes, edges, and content
- **Vector Search**: Built-in support for embeddings and semantic search
- **Property Graph**: Full property graph capabilities with typed nodes and labeled edges
- **Asynchronous API**: Modern async/await API for high-performance applications
- **PostgreSQL Backend**: Uses PostgreSQL's power for reliability and scalability

## Installation

```bash
pip install pgraf
```

### Database Setup

Ensure [pgvector](https://github.com/pgvector/pgvector) is installed.

DDL is located in [schema/pgraf.sql](schema/pgraf.sql)

```sh
psql -f schema/pgraf.sql
```

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
            title="Sample Document",
            properties={
                "tags": ["example"],
                "title": "Sample Document",
                "url": "https://www.google.com"
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
            print(f"Node: {node.type} {node.id}")
            if edge:
                print(f"  via edge: {edge.label}")

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
