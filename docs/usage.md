# Usage

## Basic Usage

### Initializing pgraf

```python
import asyncio
from pgraf import graph

async def main():
    # Initialize the graph with PostgreSQL connection
    pgraf = graph.PGraf(url="postgresql://postgres:postgres@localhost:5432/pgraf")

    try:
        # Your code here
        pass
    finally:
        # Always close connections
        await pgraf.aclose()

if __name__ == "__main__":
    asyncio.run(main())
```

### Working with Nodes

Creating nodes:

```python
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
        "url": "https://www.google.com"
    },
    mimetype="text/plain",
    content="This is a sample document that will be embedded in vector space."
)
```

Querying nodes:

```python
# Retrieve nodes by label and properties
all_people = []
async for node in pgraf.get_nodes(
    labels=["person"],
    properties={"name": "Alice"}
):
    all_people.append(node)

# Get a specific node by ID
node = await pgraf.get_node(node_id)
```

### Working with Edges

Creating edges:

```python
# Create a relationship between nodes
await pgraf.add_edge(
    source=person.id,
    target=document.id,
    labels=["CREATED"],
    properties={"timestamp": "2023-01-01"}
)
```

Querying edges:

```python
# Get edges between nodes
edges = await pgraf.get_edges(
    source=person.id,
    target=document.id,
    labels=["CREATED"]
)
```

## Graph Traversal

Traversing the graph:

```python
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
```

## Vector Search

Searching by vector similarity:

```python
# Search for semantically similar content
results = await pgraf.search(
    query="What are property graphs?",
    limit=5
)

for result in results:
    print(f"Score: {result.score}, Node: {result.node.id}")
    print(f"Content: {result.node.content[:100]}...")
```
