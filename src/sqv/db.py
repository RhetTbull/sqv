"""Database operations for SQLite viewer."""

import sqlite3
import time
from pathlib import Path


class DatabaseConnection:
    """Manages SQLite database connection and queries."""

    def __init__(self, path: str) -> None:
        """Open SQLite connection.

        Args:
            path: Path to the SQLite database file.
        """
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Database file not found: {path}")
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    def get_tables(self) -> list[str]:
        """Get list of table names."""
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [row[0] for row in cursor.fetchall()]

    def get_indices(self) -> list[str]:
        """Get list of index names."""
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        return [row[0] for row in cursor.fetchall()]

    def get_views(self) -> list[str]:
        """Get list of view names."""
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
        )
        return [row[0] for row in cursor.fetchall()]

    def get_triggers(self) -> list[str]:
        """Get list of trigger names."""
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name"
        )
        return [row[0] for row in cursor.fetchall()]

    def get_table_sql(self, name: str) -> str:
        """Get CREATE statement for a table, view, index, or trigger."""
        cursor = self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = ?", (name,)
        )
        row = cursor.fetchone()
        return row[0] if row and row[0] else ""

    def get_columns(self, table: str) -> list[tuple[str, str, bool, str | None]]:
        """Get column info for a table.

        Returns:
            List of tuples: (name, type, notnull, default_value)
        """
        cursor = self.conn.execute(f"PRAGMA table_info({table})")
        return [(row[1], row[2], bool(row[3]), row[4]) for row in cursor.fetchall()]

    def get_row_count(self, table: str) -> int:
        """Get total row count for a table."""
        cursor = self.conn.execute(f"SELECT COUNT(*) FROM [{table}]")
        return cursor.fetchone()[0]

    def fetch_rows(
        self,
        table: str,
        offset: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        order_dir: str = "ASC",
        where: str | None = None,
    ) -> tuple[list[str], list[tuple]]:
        """Fetch paginated rows from a table.

        Args:
            table: Table name
            offset: Row offset for pagination
            limit: Maximum rows to fetch
            order_by: Column to sort by
            order_dir: Sort direction (ASC or DESC)
            where: Optional WHERE clause (without WHERE keyword)

        Returns:
            Tuple of (column_names, rows)
        """
        # Get column names
        columns = [col[0] for col in self.get_columns(table)]

        # Build query
        query = f"SELECT * FROM [{table}]"
        if where:
            query += f" WHERE {where}"
        if order_by:
            query += f" ORDER BY [{order_by}] {order_dir}"
        query += f" LIMIT {limit} OFFSET {offset}"

        cursor = self.conn.execute(query)
        rows = [tuple(row) for row in cursor.fetchall()]
        return columns, rows

    def execute_sql(self, sql: str) -> tuple[list[str], list[tuple], float]:
        """Execute arbitrary SQL and return results.

        Args:
            sql: SQL statement to execute

        Returns:
            Tuple of (column_names, rows, elapsed_seconds)

        Raises:
            sqlite3.Error: If SQL execution fails
        """
        start = time.perf_counter()
        cursor = self.conn.execute(sql)
        elapsed = time.perf_counter() - start

        # Get column names from cursor description
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = [tuple(row) for row in cursor.fetchall()]
        else:
            # Non-SELECT statement (INSERT, UPDATE, DELETE, etc.)
            columns = ["rows_affected"]
            rows = [(cursor.rowcount,)]
            self.conn.commit()

        return columns, rows, elapsed
