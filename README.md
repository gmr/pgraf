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
            node_type="person",
            properties={"name": "Alice", "age": 30}
        )

        # Add a content node with vector embeddings
        document = await pgraf.add_content_node(
            title="Sample Document",
            source="user_upload",
            mimetype="text/plain",
            content="This is a sample document that will be embedded in vector space.",
            url=None,
            properties={"tags": ["sample", "documentation"]}
        )

        # Create a relationship between nodes
        await pgraf.add_edge(
            source=person.id,
            target=document.id,
            label="CREATED",
            properties={"timestamp": "2023-01-01"}
        )

        # Retrieve nodes
        all_people = await pgraf.get_nodes(
            node_types=["person"],
            properties={"name": "Alice"}
        )

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
        # Properly close connections
        await pgraf.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

## Requirements

- Python 3.12+
- PostgreSQL 14+

## License

See [LICENSE](LICENSE) for details.
