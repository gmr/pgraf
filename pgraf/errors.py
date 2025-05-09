import psycopg


class DatabaseError(psycopg.DatabaseError):
    """Raised when there is an error querying the database.

    This exception is the base class for all database-related errors in pgraf.
    It inherits from psycopg.DatabaseError and may contain additional context
    specific to pgraf operations.

    Examples:
        ```python
        try:
            await pgraf.add_node(
                labels=['person']
            )
        except DatabaseError as error:
            print(
                f'Database error occurred: {error}'
            )
        ```
    """

    ...
