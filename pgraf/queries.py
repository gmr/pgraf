"""
SQL Queries
===========
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
    SELECT proargnames
      FROM pg_proc
      JOIN pg_namespace ON pg_proc.pronamespace = pg_namespace.oid
     WHERE pg_proc.proname = %(proc_name)s
       AND pg_namespace.nspname = %(schema_name)s
"""
