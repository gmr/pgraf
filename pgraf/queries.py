"""
SQL Queries
===========
"""

GET_EDGES = """
   SELECT source,
          target,
          created_at,
          modified_at,
          labels,
          properties
     FROM pgraf.edges
"""

GET_NODES = """
   SELECT id,
          created_at,
          modified_at,
          labels,
          properties,
          mimetype,
          content
     FROM pgraf.nodes
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
