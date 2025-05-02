import psycopg


class DatabaseError(psycopg.DatabaseError):
    """Raised when there is an error querying the database"""

    ...
