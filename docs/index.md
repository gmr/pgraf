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

DDL is located in [schema/pgraf.sql](https://github.com/gmr/pgraf/blob/main/schema/pgraf.sql)

```sh
psql -f schema/pgraf.sql
```

## Requirements

- Python 3.12+
- PostgreSQL 14+
