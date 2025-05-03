CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS pgraf;

SET search_path = pgraf, public, pg_catalog;

CREATE TABLE IF NOT EXISTS nodes
(
    id          UUID                     NOT NULL PRIMARY KEY,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE,
    type        TEXT                     NOT NULL,
    properties  JSONB                    NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS content_nodes
(
    node      UUID     NOT NULL PRIMARY KEY REFERENCES nodes (id) ON DELETE CASCADE,
    title     TEXT     NOT NULL,
    source    TEXT     NOT NULL,
    mimetype  TEXT     NOT NULL,
    content   TEXT     NOT NULL,
    url       TEXT     NOT NULL,
    vector    TSVECTOR NOT NULL
);

CREATE INDEX IF NOT EXISTS content_nodes_tsvector_idx ON content_nodes USING GIN (vector);

CREATE OR REPLACE FUNCTION content_node_proprocess()
    RETURNS TRIGGER AS
$$
DECLARE
    node_type TEXT;
    vector    TSVECTOR;
BEGIN
    SELECT type
      INTO node_type
      FROM pgraf.nodes
     WHERE id = NEW.node;
    IF node_type != 'content' THEN
        RAISE EXCEPTION 'Node with ID % has label %, expected content',
            NEW.node, node_type;
    END IF;
    SELECT to_tsvector(NEW.content) INTO vector;
    NEW.vector = vector;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER content_nodes_preprocess
    BEFORE INSERT OR UPDATE ON content_nodes
    FOR EACH ROW EXECUTE FUNCTION content_node_proprocess();


CREATE TABLE IF NOT EXISTS edges
(
    source      UUID                     NOT NULL,
    target      UUID                     NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE,
    label       TEXT                     NOT NULL,
    properties  JSONB                    NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (source, target),
    FOREIGN KEY (source) REFERENCES nodes (id) ON DELETE CASCADE,
    FOREIGN KEY (target) REFERENCES nodes (id) ON DELETE CASCADE
);

CREATE OR REPLACE FUNCTION prevent_bidirectional_edges()
    RETURNS TRIGGER AS
$$
BEGIN
    IF EXISTS (SELECT 1
                 FROM pgraf.edges
                WHERE source = NEW.target
                  AND target = NEW.source) THEN
        RAISE EXCEPTION 'Bidirectional edge not allowed: edge (%, %) conflicts with existing edge',
            NEW.source, NEW.target;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_bidirectional_edges
    BEFORE INSERT ON edges
    FOR EACH ROW EXECUTE FUNCTION prevent_bidirectional_edges();


CREATE TABLE IF NOT EXISTS embeddings
(
    node  UUID        NOT NULL PRIMARY KEY REFERENCES nodes (id) ON DELETE CASCADE,
    chunk INT4        NOT NULL,
    value vector(384) NOT NULL
);

CREATE INDEX IF NOT EXISTS embeddings_embedding_idx
    ON embeddings
        USING ivfflat (value vector_cosine_ops)
    WHERE value IS NOT NULL;

-- Stored Procs for Interacting with the data

CREATE OR REPLACE FUNCTION add_node(
    IN id_in UUID,
    IN created_at_in TIMESTAMP WITH TIME ZONE,
    IN type_in TEXT,
    IN properties_in JSONB)
    RETURNS SETOF pgraf.nodes AS
$$
INSERT INTO pgraf.nodes (id, created_at, type, properties)
     VALUES (id_in, created_at_in, type_in, properties_in)
  RETURNING id, created_at, modified_at, type, properties
$$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION add_content_node(
    IN id_in UUID,
    IN created_at_in TIMESTAMP WITH TIME ZONE,
    IN type_in TEXT,
    IN properties_in JSONB,
    IN title_in TEXT,
    IN source_in TEXT,
    IN mimetype_in TEXT,
    IN content_in TEXT,
    IN url_in TEXT,
    OUT id UUID,
    OUT created_at TIMESTAMP WITH TIME ZONE,
    OUT modified_at TIMESTAMP WITH TIME ZONE,
    OUT type TEXT,
    OUT properties JSONB,
    OUT title TEXT,
    OUT source TEXT,
    OUT mimetype TEXT,
    OUT content TEXT,
    OUT url TEXT
)
AS $$
BEGIN
    INSERT INTO pgraf.nodes(id, created_at, type, properties)
         VALUES (id_in, created_at_in, type_in, properties_in)
      RETURNING nodes.id, nodes.created_at, nodes.modified_at, nodes.type, nodes.properties
           INTO id, created_at, modified_at, type, properties;

    INSERT INTO pgraf.content_nodes(node, title, source, mimetype, content, url)
         VALUES (id, title_in, source_in, mimetype_in,
                 content_in, url_in);

    -- Set output variables for content_nodes fields
    title := title_in;
    source := source_in;
    mimetype := mimetype_in;
    content := content_in;
    url := url_in;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pgraf.delete_node(
    IN id_in UUID,
    OUT count INTEGER) AS
$$
WITH deleted AS (
    DELETE FROM pgraf.nodes
          WHERE id = id_in
      RETURNING *)
SELECT count(*);
$$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION pgraf.get_node(
    IN id_in UUID,
    OUT id UUID,
    OUT created_at TIMESTAMP WITH TIME ZONE,
    OUT modified_at TIMESTAMP WITH TIME ZONE,
    OUT type TEXT,
    OUT properties JSONB,
    OUT title TEXT,
    OUT source TEXT,
    OUT mimetype TEXT,
    OUT content TEXT,
    OUT url TEXT
    )  RETURNS SETOF RECORD AS $$
   SELECT a.id,
          a.created_at,
          a.modified_at,
          a.type,
          a.properties,
          b.title,
          b.source,
          b.mimetype,
          b.content,
          b.url
     FROM pgraf.nodes AS a
LEFT JOIN pgraf.content_nodes AS b
       ON b.node = a.id
    WHERE a.id = id_in;
$$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION update_node(
    IN id_in UUID,
    IN modified_at_in TIMESTAMP WITH TIME ZONE,
    IN type_in TEXT,
    IN properties_in JSONB)
    RETURNS SETOF pgraf.nodes AS
$$
   UPDATE pgraf.nodes
      SET modified_at = modified_at_in,
          type        = type_in,
          properties  = properties_in
    WHERE nodes.id = id_in
RETURNING *
$$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION update_content_node(
    IN id_in UUID,
    IN properties_in JSONB,
    IN title_in TEXT,
    IN source_in TEXT,
    IN mimetype_in TEXT,
    IN content_in TEXT,
    IN url_in TEXT,
    OUT id UUID,
    OUT created_at TIMESTAMP WITH TIME ZONE,
    OUT modified_at TIMESTAMP WITH TIME ZONE,
    OUT type TEXT,
    OUT properties JSONB,
    OUT title TEXT,
    OUT source TEXT,
    OUT mimetype TEXT,
    OUT content TEXT,
    OUT url TEXT
    ) AS $$
BEGIN
       UPDATE pgraf.nodes
          SET type = 'content',
              properties = properties_in,
              modified_at = CURRENT_TIMESTAMP
        WHERE nodes.id = id_in
    RETURNING nodes.id,
              nodes.created_at,
              nodes.modified_at,
              nodes.type,
              nodes.properties
         INTO id, created_at, modified_at, type, properties;

       UPDATE pgraf.content_nodes
          SET title = title_in,
              source = source_in,
              mimetype = mimetype_in,
              content = content_in,
              url = url_in
        WHERE content_nodes.node = id_in
    RETURNING content_nodes.title,
              content_nodes.source,
              content_nodes.mimetype,
              content_nodes.content,
              content_nodes.url
         INTO title, source, mimetype, content, url;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Content node with ID % not found', id_in;
    END IF;
END;
$$ LANGUAGE plpgsql;



CREATE OR REPLACE FUNCTION add_edge(
    IN source_in UUID,
    IN target_in UUID,
    IN created_at_in TIMESTAMP WITH TIME ZONE,
    IN label_in TEXT,
    IN properties_in JSONB)
    RETURNS SETOF pgraf.edges AS
$$
INSERT INTO pgraf.edges (source, target, created_at, label, properties)
     VALUES (source_in, target_in, created_at_in, label_in, properties_in)
  RETURNING source, target, created_at, modified_at, label, properties
$$ LANGUAGE SQL;


CREATE OR REPLACE FUNCTION pgraf.delete_edge(
    IN source_in UUID,
    IN target_in UUID,
    OUT count INTEGER) AS
$$
WITH deleted AS (
    DELETE FROM pgraf.edges
          WHERE (source = source_in AND target = target_in)
             OR (source = target_in AND target = source_in)
      RETURNING *)
SELECT count(*);
$$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION pgraf.get_edge(IN source_in UUID, IN target_in UUID)
    RETURNS SETOF pgraf.edges AS
$$
SELECT source, target, created_at, modified_at, label, properties
  FROM pgraf.edges
 WHERE (source = source_in AND target = target_in)
    OR (source = target_in AND target = source_in)
$$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION update_edge(
    IN source_in UUID,
    IN target_in UUID,
    IN modified_at_in TIMESTAMP WITH TIME ZONE,
    IN label_in TEXT,
    IN properties_in JSONB)
    RETURNS SETOF pgraf.edges AS
$$
    -- Intentionally don't change when the record was created
   UPDATE pgraf.edges
      SET modified_at = modified_at_in,
          label       = label_in,
          properties  = properties_in
    WHERE (source = source_in AND target = target_in)
       OR (source = target_in AND target = source_in)
RETURNING *
$$ LANGUAGE SQL;
