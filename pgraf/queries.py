"""
SQL Queries
===========
"""

PROC_NAMES = """
    SELECT proargnames
      FROM pg_proc
      JOIN pg_namespace ON pg_proc.pronamespace = pg_namespace.oid
     WHERE pg_proc.proname = %(proc_name)s
       AND pg_namespace.nspname = %(schema_name)s
"""
