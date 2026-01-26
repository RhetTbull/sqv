"""Pytest fixtures for sqv tests."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from sqv.db import DatabaseConnection


@pytest.fixture
def sample_db_path() -> Path:
    """Create a temporary SQLite database with sample data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create tables
    cursor.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            age INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE empty_table (
            id INTEGER PRIMARY KEY,
            value TEXT
        )
    """
    )

    # Create index
    cursor.execute("CREATE INDEX idx_users_email ON users(email)")
    cursor.execute("CREATE INDEX idx_posts_user ON posts(user_id)")

    # Create view
    cursor.execute(
        """
        CREATE VIEW user_post_counts AS
        SELECT u.id, u.name, COUNT(p.id) as post_count
        FROM users u
        LEFT JOIN posts p ON u.id = p.user_id
        GROUP BY u.id
    """
    )

    # Create trigger
    cursor.execute(
        """
        CREATE TRIGGER update_timestamp
        AFTER UPDATE ON users
        BEGIN
            UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END
    """
    )

    # Insert sample data
    users_data = [
        ("Alice", "alice@example.com", 30),
        ("Bob", "bob@example.com", 25),
        ("Charlie", "charlie@example.com", 35),
        ("Diana", "diana@example.com", 28),
        ("Eve", "eve@example.com", 32),
    ]
    cursor.executemany(
        "INSERT INTO users (name, email, age) VALUES (?, ?, ?)", users_data
    )

    posts_data = [
        (1, "Hello World", "First post content"),
        (1, "Second Post", "More content here"),
        (2, "Bob's Post", "Bob writes something"),
        (3, "Charlie's Thoughts", None),
    ]
    cursor.executemany(
        "INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)", posts_data
    )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink(missing_ok=True)


@pytest.fixture
def db(sample_db_path: Path) -> DatabaseConnection:
    """Create a DatabaseConnection to the sample database."""
    conn = DatabaseConnection(str(sample_db_path))
    yield conn
    conn.close()


@pytest.fixture
def blob_db_path() -> Path:
    """Create a database with binary data for BLOB handling tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE blobs (
            id INTEGER PRIMARY KEY,
            name TEXT,
            data BLOB
        )
    """
    )

    # Insert rows with binary data, including bytes that look like Rich markup
    blob_data = [
        (1, "simple", b"\x00\x01\x02\x03"),
        (2, "with_brackets", b"[test]data[/test]"),
        (3, "large", b"\xb4|\x05xSg\xfb\xfeyO\x926" * 1000),
    ]
    cursor.executemany("INSERT INTO blobs (id, name, data) VALUES (?, ?, ?)", blob_data)

    conn.commit()
    conn.close()

    yield db_path

    db_path.unlink(missing_ok=True)


@pytest.fixture
def large_db_path() -> Path:
    """Create a database with many rows for pagination testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE numbers (
            id INTEGER PRIMARY KEY,
            value INTEGER,
            label TEXT
        )
    """
    )

    # Insert 500 rows
    data = [(i, i * 10, f"Label {i}") for i in range(1, 501)]
    cursor.executemany("INSERT INTO numbers (id, value, label) VALUES (?, ?, ?)", data)

    conn.commit()
    conn.close()

    yield db_path

    db_path.unlink(missing_ok=True)
