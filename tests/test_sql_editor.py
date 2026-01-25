"""Tests for SQL editor widgets."""

import sqlite3

import pytest

from sqv.db import DatabaseConnection


def test_execute_select(db: DatabaseConnection) -> None:
    """Test executing SELECT query."""
    columns, rows, elapsed = db.execute_sql("SELECT * FROM users")

    assert len(columns) == 5
    assert len(rows) == 5
    assert elapsed >= 0


def test_execute_select_with_where(db: DatabaseConnection) -> None:
    """Test executing SELECT with WHERE clause."""
    columns, rows, _ = db.execute_sql("SELECT name FROM users WHERE age > 30")

    assert columns == ["name"]
    assert len(rows) == 2  # Charlie (35) and Eve (32)


def test_execute_select_with_join(db: DatabaseConnection) -> None:
    """Test executing SELECT with JOIN."""
    columns, rows, _ = db.execute_sql(
        """
        SELECT u.name, p.title
        FROM users u
        JOIN posts p ON u.id = p.user_id
        ORDER BY u.name, p.title
    """
    )

    assert "name" in columns
    assert "title" in columns
    assert len(rows) == 4


def test_execute_aggregate(db: DatabaseConnection) -> None:
    """Test executing aggregate query."""
    columns, rows, _ = db.execute_sql("SELECT COUNT(*) as cnt FROM users")

    assert columns == ["cnt"]
    assert rows[0][0] == 5


def test_execute_insert(db: DatabaseConnection) -> None:
    """Test executing INSERT statement."""
    columns, rows, _ = db.execute_sql(
        "INSERT INTO users (name, email, age) VALUES ('New User', 'new@test.com', 40)"
    )

    assert columns == ["rows_affected"]
    assert rows[0][0] == 1

    # Verify
    _, check_rows, _ = db.execute_sql("SELECT * FROM users WHERE name = 'New User'")
    assert len(check_rows) == 1


def test_execute_update(db: DatabaseConnection) -> None:
    """Test executing UPDATE statement."""
    columns, rows, _ = db.execute_sql("UPDATE users SET age = age + 1 WHERE age < 30")

    assert columns == ["rows_affected"]
    assert rows[0][0] == 2  # Bob (25) and Diana (28)


def test_execute_delete(db: DatabaseConnection) -> None:
    """Test executing DELETE statement."""
    # First insert a row to delete
    db.execute_sql(
        "INSERT INTO users (name, email, age) VALUES ('ToDelete', 'del@test.com', 99)"
    )

    columns, rows, _ = db.execute_sql("DELETE FROM users WHERE name = 'ToDelete'")

    assert columns == ["rows_affected"]
    assert rows[0][0] == 1


def test_execute_error_invalid_table(db: DatabaseConnection) -> None:
    """Test error handling for invalid table."""
    with pytest.raises(Exception) as exc_info:
        db.execute_sql("SELECT * FROM nonexistent_table")

    assert (
        "nonexistent_table" in str(exc_info.value).lower()
        or "no such table" in str(exc_info.value).lower()
    )


def test_execute_error_syntax(db: DatabaseConnection) -> None:
    """Test error handling for syntax error."""
    with pytest.raises(sqlite3.Error):
        db.execute_sql("SELEC * FROM users")


def test_execute_error_invalid_column(db: DatabaseConnection) -> None:
    """Test error handling for invalid column."""
    with pytest.raises(sqlite3.Error):
        db.execute_sql("SELECT nonexistent_column FROM users")


def test_timing_measurement(db: DatabaseConnection) -> None:
    """Test that timing is measured."""
    _, _, elapsed = db.execute_sql("SELECT * FROM users")

    assert isinstance(elapsed, float)
    assert elapsed >= 0
    assert elapsed < 10  # Should be much faster than 10 seconds


def test_multiple_statements_error(db: DatabaseConnection) -> None:
    """Test that multiple statements raise an error."""
    with pytest.raises(sqlite3.ProgrammingError):
        db.execute_sql("SELECT 1; SELECT 2;")
