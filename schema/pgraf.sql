CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS pgraf;

SET search_path=pgraf, public, pg_catalog;

CREATE TABLE IF NOT EXISTS nodes (
    id           UUID                      NOT NULL  PRIMARY KEY,
    created_at   TIMESTAMP WITH TIME ZONE  NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    modified_at  TIMESTAMP WITH TIME ZONE,
    type         TEXT                      NOT NULL,
    properties   JSONB                     NOT NULL  DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS edges (
    source       UUID                      NOT NULL,
    target       UUID                      NOT NULL,
    created_at   TIMESTAMP WITH TIME ZONE  NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    modified_at  TIMESTAMP WITH TIME ZONE,
    label        TEXT                      NOT NULL,
    properties   JSONB                     NOT NULL  DEFAULT '{}'::jsonb,
    PRIMARY KEY (source, target),
    FOREIGN KEY (source) REFERENCES nodes (id) ON DELETE CASCADE,
    FOREIGN KEY (target) REFERENCES nodes (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS embeddings (
    node   UUID          NOT NULL  PRIMARY KEY  REFERENCES nodes(id) ON DELETE CASCADE,
    chunk  INT4          NOT NULL,
    value  vector(384)  NOT NULL
);

CREATE INDEX IF NOT EXISTS embeddings_embedding_idx
          ON embeddings
       USING ivfflat (value vector_cosine_ops)
       WHERE value IS NOT NULL;

CREATE TABLE IF NOT EXISTS document_nodes (
    node         UUID       NOT NULL  PRIMARY KEY  REFERENCES nodes(id) ON DELETE CASCADE,
    title        TEXT       NOT NULL,
    type         TEXT       NOT NULL,
    content      TEXT       NOT NULL,
    url          TEXT       NOT NULL,
    vector       TSVECTOR   NOT NULL
);

CREATE INDEX IF NOT EXISTS document_nodes_tsvector_idx ON document_nodes USING GIN (vector);

CREATE OR REPLACE FUNCTION document_node_proprocess()
RETURNS TRIGGER AS $$
DECLARE
  node_type TEXT;
  vector TSVECTOR;
BEGIN
  SELECT type INTO node_type
    FROM nodes
   WHERE id = NEW.node;
  IF node_type != 'document' THEN
    RAISE EXCEPTION 'Node with ID % has label %, expected document',
                    NEW.node, node_type;
  END IF;
  SELECT to_tsvector(NEW.content) INTO vector;
  NEW.vector = vector;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER document_nodes_preprocess BEFORE INSERT OR UPDATE ON document_nodes
  FOR EACH ROW EXECUTE FUNCTION document_node_proprocess();
