# Overview

pgraf provides a high-performance property graph database implementation built on top of PostgreSQL, with
specific optimizations for AI agent use cases.

## What is a Property Graph?

A property graph is a graph data structure that consists of:

* **Nodes**: Entities with properties and labels
* **Edges**: Relationships between nodes with labels and properties
* **Properties**: Key-value pairs attached to both nodes and edges
* **Labels**: Categorization tags for nodes and edges

pgraf enhances this model with:

* Strong typing via Pydantic models
* Vector embeddings for semantic search
* Full-text content storage and retrieval
* Asynchronous API for high concurrency

## Use Cases

pgraf is particularly well-suited for:

* AI agent knowledge graphs
* Semantic search applications
* Document networks with relationships
* Complex data modeling with typed relationships
* Applications requiring both graph and vector search capabilities

## Architecture

pgraf uses:

* PostgreSQL as the storage backend
* pgvector for vector operations
* Pydantic for model validation
* Async Python for high-performance operations

The architecture consists of several key components:

* **Graph Engine**: Core graph operations (nodes, edges, traversals)
* **Vector Search**: Embedding management and similarity search
* **Type System**: Strongly-typed models for graph elements
* **Query Layer**: Composable query building system
