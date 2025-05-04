"""
SQL Queries
===========
"""

DELETE_EMBEDDINGS = """
DELETE FROM pgraf.embeddings
      WHERE node = %(node)s
"""

GET_EDGE_LABELS = """
  SELECT DISTINCT label
    FROM pgraf.edges
ORDER BY label;
"""

GET_NODE_TYPES = """
  SELECT DISTINCT type
    FROM pgraf.nodes
ORDER BY type;
"""

GET_NODES = """
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
"""

PROC_NAMES = """
SELECT REPLACE(arg_name, '_in', '') AS arg_name,
       arg_type
FROM (
   SELECT unnest(p.proargnames) AS arg_name,
          format_type(unnest(p.proargtypes), NULL) AS arg_type,
          array_position(p.proargnames, unnest(p.proargnames)) AS pos
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
   WHERE p.proname = %(proc_name)s
     AND n.nspname = %(schema_name)s
) subq
WHERE arg_name LIKE '%%_in'
ORDER BY pos;
"""
