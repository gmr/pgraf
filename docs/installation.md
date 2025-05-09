# Installation

## Requirements

* Python 3.12+
* PostgreSQL 14+
* pgvector extension for PostgreSQL

## Installing pgraf

Install pgraf using pip:

```bash
pip install pgraf
```

For development, you can install the development dependencies:

```bash
pip install -e ".[dev]"
```

For building documentation:

```bash
pip install -e ".[docs]"
```

## Database Setup

1. Ensure pgvector is installed in your PostgreSQL instance

   Follow the installation instructions at: https://github.com/pgvector/pgvector

2. Create a database for pgraf:

   ```bash
   createdb pgraf
   ```

3. Apply the schema:

   ```bash
   psql -d pgraf -f schema/pgraf.sql
   ```

## Docker Setup

A Docker Compose configuration is included for easier development:

```bash
docker-compose up -d
```

This will start a PostgreSQL instance with pgvector pre-installed and the pgraf schema applied.
