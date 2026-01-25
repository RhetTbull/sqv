"""Tests for structure viewer widgets."""

from sqv.db import DatabaseConnection


class TestStructureViewer:
    """Tests for structure viewer functionality."""

    def test_structure_tree_tables(self, db: DatabaseConnection) -> None:
        """Test that tables are retrieved correctly."""
        tables = db.get_tables()
        assert len(tables) == 3
        assert "users" in tables
        assert "posts" in tables
        assert "empty_table" in tables

    def test_structure_tree_indices(self, db: DatabaseConnection) -> None:
        """Test that indices are retrieved correctly."""
        indices = db.get_indices()
        assert "idx_users_email" in indices
        assert "idx_posts_user" in indices

    def test_structure_tree_views(self, db: DatabaseConnection) -> None:
        """Test that views are retrieved correctly."""
        views = db.get_views()
        assert "user_post_counts" in views

    def test_structure_tree_triggers(self, db: DatabaseConnection) -> None:
        """Test that triggers are retrieved correctly."""
        triggers = db.get_triggers()
        assert "update_timestamp" in triggers

    def test_table_columns(self, db: DatabaseConnection) -> None:
        """Test that table columns are retrieved correctly."""
        columns = db.get_columns("users")
        col_names = [c[0] for c in columns]

        assert "id" in col_names
        assert "name" in col_names
        assert "email" in col_names
        assert "age" in col_names
        assert "created_at" in col_names

    def test_table_sql_display(self, db: DatabaseConnection) -> None:
        """Test that CREATE SQL is retrieved correctly."""
        sql = db.get_table_sql("users")
        assert "CREATE TABLE" in sql
        assert "users" in sql
        assert "name TEXT NOT NULL" in sql

    def test_view_sql_display(self, db: DatabaseConnection) -> None:
        """Test that view SQL is retrieved correctly."""
        sql = db.get_table_sql("user_post_counts")
        assert "CREATE VIEW" in sql
        assert "user_post_counts" in sql

    def test_index_sql_display(self, db: DatabaseConnection) -> None:
        """Test that index SQL is retrieved correctly."""
        sql = db.get_table_sql("idx_users_email")
        assert "CREATE INDEX" in sql
        assert "users" in sql
        assert "email" in sql

    def test_trigger_sql_display(self, db: DatabaseConnection) -> None:
        """Test that trigger SQL is retrieved correctly."""
        sql = db.get_table_sql("update_timestamp")
        assert "CREATE TRIGGER" in sql
        assert "update_timestamp" in sql
