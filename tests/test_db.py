"""Tests for database operations."""

import sqlite3
from pathlib import Path

import pytest

from sqv.db import DatabaseConnection


def test_open_nonexistent_file(tmp_path: Path) -> None:
    """Test opening a nonexistent file raises error."""
    with pytest.raises(FileNotFoundError):
        DatabaseConnection(str(tmp_path / "nonexistent.db"))


def test_get_tables(db: DatabaseConnection) -> None:
    """Test getting list of tables."""
    tables = db.get_tables()
    assert "users" in tables
    assert "posts" in tables
    assert "empty_table" in tables
    assert len(tables) == 3


def test_get_indices(db: DatabaseConnection) -> None:
    """Test getting list of indices."""
    indices = db.get_indices()
    assert "idx_users_email" in indices
    assert "idx_posts_user" in indices


def test_get_views(db: DatabaseConnection) -> None:
    """Test getting list of views."""
    views = db.get_views()
    assert "user_post_counts" in views


def test_get_triggers(db: DatabaseConnection) -> None:
    """Test getting list of triggers."""
    triggers = db.get_triggers()
    assert "update_timestamp" in triggers


def test_get_table_sql(db: DatabaseConnection) -> None:
    """Test getting CREATE statement."""
    sql = db.get_table_sql("users")
    assert "CREATE TABLE" in sql
    assert "users" in sql
    assert "name TEXT NOT NULL" in sql


def test_get_columns(db: DatabaseConnection) -> None:
    """Test getting column info."""
    columns = db.get_columns("users")
    col_names = [c[0] for c in columns]

    assert "id" in col_names
    assert "name" in col_names
    assert "email" in col_names
    assert "age" in col_names

    # Check name column is NOT NULL
    name_col = next(c for c in columns if c[0] == "name")
    assert name_col[1] == "TEXT"
    assert name_col[2] is True  # notnull


def test_get_row_count(db: DatabaseConnection) -> None:
    """Test getting row count."""
    assert db.get_row_count("users") == 5
    assert db.get_row_count("posts") == 4
    assert db.get_row_count("empty_table") == 0


def test_fetch_rows_basic(db: DatabaseConnection) -> None:
    """Test basic row fetching."""
    columns, rows = db.fetch_rows("users")
    assert len(columns) == 5
    assert len(rows) == 5
    assert "name" in columns


def test_fetch_rows_with_limit(db: DatabaseConnection) -> None:
    """Test row fetching with limit."""
    columns, rows = db.fetch_rows("users", limit=2)
    assert len(rows) == 2


def test_fetch_rows_with_offset(db: DatabaseConnection) -> None:
    """Test row fetching with offset."""
    _, all_rows = db.fetch_rows("users")
    _, offset_rows = db.fetch_rows("users", offset=2)

    assert len(offset_rows) == 3
    assert offset_rows[0] == all_rows[2]


def test_fetch_rows_with_order(db: DatabaseConnection) -> None:
    """Test row fetching with ordering."""
    _, rows_asc = db.fetch_rows("users", order_by="name", order_dir="ASC")
    _, rows_desc = db.fetch_rows("users", order_by="name", order_dir="DESC")

    # Get name column index
    columns, _ = db.fetch_rows("users")
    name_idx = columns.index("name")

    assert rows_asc[0][name_idx] == "Alice"
    assert rows_desc[0][name_idx] == "Eve"


def test_fetch_rows_with_where(db: DatabaseConnection) -> None:
    """Test row fetching with WHERE clause."""
    _, rows = db.fetch_rows("users", where="age > 30")
    assert len(rows) == 2  # Charlie (35) and Eve (32)


def test_execute_sql_select(db: DatabaseConnection) -> None:
    """Test executing SELECT query."""
    columns, rows, elapsed = db.execute_sql("SELECT name FROM users WHERE age < 30")

    assert columns == ["name"]
    assert len(rows) == 2  # Bob (25) and Diana (28)
    assert elapsed >= 0


def test_execute_sql_insert(db: DatabaseConnection) -> None:
    """Test executing INSERT statement."""
    columns, rows, _ = db.execute_sql(
        "INSERT INTO users (name, email, age) VALUES ('Test', 'test@test.com', 20)"
    )

    assert columns == ["rows_affected"]
    assert rows[0][0] == 1

    # Verify insert
    assert db.get_row_count("users") == 6


def test_execute_sql_error(db: DatabaseConnection) -> None:
    """Test executing invalid SQL raises error."""
    with pytest.raises(sqlite3.Error):
        db.execute_sql("SELECT * FROM nonexistent_table")


def test_execute_sql_syntax_error(db: DatabaseConnection) -> None:
    """Test executing SQL with syntax error raises error."""
    with pytest.raises(sqlite3.Error):
        db.execute_sql("SELEC * FROM users")


def test_pagination(large_db_path: Path) -> None:
    """Test paginating through many rows."""
    db = DatabaseConnection(str(large_db_path))

    try:
        total = db.get_row_count("numbers")
        assert total == 500

        # First page
        _, page1 = db.fetch_rows("numbers", offset=0, limit=100)
        assert len(page1) == 100
        assert page1[0][0] == 1

        # Middle page
        _, page3 = db.fetch_rows("numbers", offset=200, limit=100)
        assert len(page3) == 100
        assert page3[0][0] == 201

        # Last partial page
        _, last_page = db.fetch_rows("numbers", offset=450, limit=100)
        assert len(last_page) == 50
        assert last_page[-1][0] == 500

    finally:
        db.close()
