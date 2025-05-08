CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS pgraf;

SET search_path = pgraf, public, pg_catalog;

CREATE TABLE IF NOT EXISTS nodes
(
    id          UUID                     NOT NULL PRIMARY KEY,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE,
    labels      TEXT[]                   NOT NULL,
    properties  JSONB                    NOT NULL DEFAULT '{}'::jsonb,
    mimetype    TEXT,
    content     TEXT,
    vector      TSVECTOR
);

-- Example Unique Indexes - will depend on your data model
CREATE UNIQUE INDEX confluence_page_id ON pgraf.nodes ((properties->'page_id'));
CREATE UNIQUE INDEX user_email_address ON pgraf.nodes ((properties->'email_address'));

CREATE INDEX IF NOT EXISTS node_tsvector_idx ON nodes USING GIN (vector);

CREATE TABLE IF NOT EXISTS edges
(
    source      UUID                     NOT NULL,
    target      UUID                     NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE,
    labels      TEXT[]                   NOT NULL,
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
    node  UUID        NOT NULL  REFERENCES nodes (id) ON DELETE CASCADE,
    chunk INT4        NOT NULL,
    value vector(384) NOT NULL,
    PRIMARY KEY (node, chunk)
);

CREATE INDEX IF NOT EXISTS embeddings_embedding_idx
    ON embeddings
        USING ivfflat (value vector_cosine_ops)
    WHERE value IS NOT NULL;

-- Stored Procs for Interacting with the data

CREATE OR REPLACE FUNCTION add_node(
    IN id_in UUID,
    IN created_at_in TIMESTAMP WITH TIME ZONE,
    IN modified_at_in TIMESTAMP WITH TIME ZONE,
    IN labels_in TEXT[],
    IN properties_in JSONB,
    IN mimetype_in TEXT,
    IN content_in TEXT,
    OUT id UUID,
    OUT created_at TIMESTAMP WITH TIME ZONE,
    OUT modified_at TIMESTAMP WITH TIME ZONE,
    OUT labels TEXT[],
    OUT properties JSONB,
    OUT mimetype TEXT,
    OUT content TEXT)
    RETURNS SETOF record AS $$
INSERT INTO pgraf.nodes (id, created_at, modified_at, labels, properties, mimetype, content, vector)
     VALUES (id_in, created_at_in, modified_at_in, labels_in,
             properties_in, mimetype_in, content_in, to_tsvector(content_in))
  RETURNING id, created_at, modified_at, labels, properties, mimetype, content;
$$ LANGUAGE sql;

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
    OUT labels TEXT[],
    OUT properties JSONB,
    OUT mimetype TEXT,
    OUT content TEXT
    )  RETURNS SETOF RECORD AS $$
   SELECT n.id,
          n.created_at,
          n.modified_at,
          n.labels,
          n.properties,
          n.mimetype,
          n.content
     FROM pgraf.nodes AS n
    WHERE n.id = id_in;
$$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION update_node(
    IN id_in UUID,
    IN labels_in TEXT,
    IN properties_in JSONB,
    IN mimetype_in TEXT,
    IN content_in TEXT,
    OUT id UUID,
    OUT created_at TIMESTAMP WITH TIME ZONE,
    OUT modified_at TIMESTAMP WITH TIME ZONE,
    OUT labels TEXT[],
    OUT properties JSONB,
    OUT mimetype TEXT,
    OUT content TEXT)
RETURNS SETOF record AS $$
BEGIN
   -- Remove previous embeddings if they exist
   DELETE
     FROM pgraf.embeddings
    WHERE node = id_in;
   -- Update the node and vectorize the content
   UPDATE pgraf.nodes
      SET modified_at = CURRENT_TIMESTAMP,
          labels = labels_in,
          properties = properties_in,
          mimetype = mimetype_in,
          content = to_tsvector(content_in)
    WHERE nodes.id = id_in;
   -- Return the updated record
   RETURN QUERY
   SELECT n.id,
          n.created_at,
          n.modified_at,
          n.labels,
          n.properties,
          n.mimetype,
          n.content
     FROM pgraf.nodes AS n
    WHERE n.id = id_in;
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
BEGIN
    IF source_in = target_in THEN
        RAISE EXCEPTION 'Source % and Target are the same node', source_in;
    END IF;
    RETURN QUERY
    INSERT INTO pgraf.edges (source, target, created_at, label, properties)
         VALUES (source_in, target_in, created_at_in, label_in, properties_in)
      RETURNING source, target, created_at, modified_at, label, properties;
END
$$ LANGUAGE plpgsql;

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
SELECT source, target, created_at, modified_at, labels, properties
  FROM pgraf.edges
 WHERE (source = source_in AND target = target_in)
    OR (source = target_in AND target = source_in)
$$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION update_edge(
    IN source_in UUID,
    IN target_in UUID,
    IN modified_at_in TIMESTAMP WITH TIME ZONE,
    IN labels_in TEXT[],
    IN properties_in JSONB)
    RETURNS SETOF pgraf.edges AS
$$
    -- Intentionally don't change when the record was created
   UPDATE pgraf.edges
      SET modified_at = modified_at_in,
          labels = labels_in,
          properties = properties_in
    WHERE (source = source_in AND target = target_in)
       OR (source = target_in AND target = source_in)
RETURNING *
$$ LANGUAGE SQL;


CREATE OR REPLACE FUNCTION add_embedding(
    IN node_in UUID,
    IN chunk_in INT4,
    IN value_in vector(384),
    OUT success BOOL) AS
$$
    WITH inserted AS (
        INSERT INTO pgraf.embeddings (node, chunk, value)
             VALUES (node_in, chunk_in, value_in)
          RETURNING node, chunk)
    SELECT EXISTS (SELECT 1 FROM inserted) AS success;
$$ LANGUAGE SQL;

CREATE OR REPLACE FUNCTION pgraf.traverse(
    start_node_in UUID,
    node_labels_in TEXT[] DEFAULT NULL,
    edge_labels_in TEXT[] DEFAULT NULL,
    direction_in TEXT DEFAULT 'outgoing',
    max_depth_in INTEGER DEFAULT 1,
    limit_in INTEGER DEFAULT 25
)
RETURNS TABLE (
    node_id UUID,
    node_created_at TIMESTAMP WITH TIME ZONE,
    node_modified_at TIMESTAMP WITH TIME ZONE,
    node_labels TEXT[],
    node_properties JSONB,
    node_mimetype TEXT,
    node_content TEXT,
    edge_source UUID,
    edge_target UUID,
    edge_created_at TIMESTAMP WITH TIME ZONE,
    edge_modified_at TIMESTAMP WITH TIME ZONE,
    edge_labels TEXT[],
    edge_properties JSONB,
    depth INTEGER
) AS $$
BEGIN
    IF direction_in NOT IN ('outgoing', 'incoming', 'both') THEN
        RAISE EXCEPTION 'Invalid direction: %. Must be one of: outgoing, incoming, both',
                        direction_in;
    END IF;

    RETURN QUERY
    WITH RECURSIVE traversal AS (
        SELECT id,
               created_at,
               modified_at,
               labels,
               properties,
               mimetype,
               content,
               NULL::UUID AS edge_source,
               NULL::UUID AS edge_target,
               NULL::TIMESTAMP WITH TIME ZONE AS edge_created_at,
               NULL::TIMESTAMP WITH TIME ZONE AS edge_modified_at,
               NULL::TEXT[] AS edge_labels,
               NULL::JSONB AS edge_properties,
               0 AS depth
          FROM pgraf.nodes
         WHERE id = start_node_in
           AND (node_labels_in IS NULL OR labels && node_labels_in)
         UNION ALL
        -- Recursive case: traverse to connected nodes
        SELECT next_n.id,
               next_n.created_at,
               next_n.modified_at,
               next_n.labels,
               next_n.properties,
               next_n.mimetype,
               next_n.content,
               e.source,
               e.target,
               e.created_at,
               e.modified_at,
               e.labels,
               e.properties,
               t.depth + 1
          FROM traversal t
          JOIN pgraf.edges e ON
                -- Handle direction logic
          CASE WHEN direction_in = 'outgoing' THEN e.source = t.id
               WHEN direction_in = 'incoming' THEN e.target = t.id
               WHEN direction_in = 'both' THEN e.source = t.id OR e.target = t.id
           END
          JOIN pgraf.nodes next_n ON
            -- Connect to the correct node based on direction
          CASE WHEN direction_in = 'outgoing' THEN next_n.id = e.target
               WHEN direction_in = 'incoming' THEN next_n.id = e.source
               WHEN direction_in = 'both' AND e.source = t.id THEN next_n.id = e.target
               WHEN direction_in = 'both' AND e.target = t.id THEN next_n.id = e.source
           END
         WHERE t.depth < max_depth_in
           AND (node_labels_in IS NULL OR next_n.labels && node_labels_in)
           AND (edge_labels_in IS NULL OR e.labels && edge_labels_in))
        SELECT *
          FROM traversal
      ORDER BY greatest(created_at, modified_at) DESC
         LIMIT limit_in;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pgraf.search(
    query_in TEXT,
    embeddings_in vector(384),
    properties_in JSONB DEFAULT NULL,
    labels_in TEXT[] DEFAULT NULL,
    similarity_in FLOAT4 DEFAULT 0.5,
    limit_in INT4 DEFAULT 100,
    OUT id UUID,
    OUT created_at TIMESTAMP WITH TIME ZONE,
    OUT modified_at TIMESTAMP WITH TIME ZONE,
    OUT labels TEXT[],
    OUT properties JSONB,
    OUT mimetype TEXT,
    OUT content TEXT,
    OUT similarity FLOAT4
) RETURNS SETOF RECORD AS $$
    WITH embedding_matches AS (
        SELECT e.node,
               max(CAST(1 - (e.value <=> embeddings_in) AS float)) as similarity
          FROM pgraf.embeddings AS e
          JOIN pgraf.nodes AS n
            ON n.id = e.node
         WHERE vector_dims(e.value) = vector_dims(embeddings_in)
           AND 1 - (e.value <=> embeddings_in) > similarity_in
           AND (labels_in IS NULL OR n.labels && labels_in)
           AND (properties_in IS NULL OR n.properties @> properties_in)
      GROUP BY e.node
      ORDER BY similarity DESC
         LIMIT limit_in),
    text_matches AS (
        SELECT n.id AS node,
               ts_rank_cd(n.vector, plainto_tsquery(query_in)) AS similarity
          FROM pgraf.nodes AS n
         WHERE n.vector @@ plainto_tsquery(query_in)
           AND ts_rank_cd(n.vector, plainto_tsquery(query_in)) > similarity_in
           AND (labels_in IS NULL OR n.labels && labels_in)
           AND (properties_in IS NULL OR n.properties @> properties_in)
      ORDER BY similarity DESC
         LIMIT limit_in),
     combined_results AS (
        SELECT COALESCE(em.node, tm.node) AS node,
               GREATEST(COALESCE(tm.similarity, 0), COALESCE(em.similarity, 0))  AS similarity
          FROM embedding_matches em
          FULL OUTER JOIN text_matches tm ON em.node = tm.node
      ORDER BY similarity DESC
         LIMIT 100)
       SELECT n.id,
              n.created_at,
              n.modified_at,
              n.labels,
              n.properties,
              n.mimetype,
              n.content,
              cr.similarity
         FROM combined_results AS cr
         JOIN pgraf.nodes AS n
           ON n.id = cr.node
     ORDER BY cr.similarity DESC
        LIMIT limit_in
$$ LANGUAGE sql;
