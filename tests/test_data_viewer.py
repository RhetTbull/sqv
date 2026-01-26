"""Tests for data viewer widgets."""

from pathlib import Path

from sqv.db import DatabaseConnection


def test_load_table_data(db: DatabaseConnection) -> None:
    """Test loading table data."""
    columns, rows = db.fetch_rows("users")

    assert len(columns) == 5
    assert len(rows) == 5


def test_sorting_asc(db: DatabaseConnection) -> None:
    """Test sorting data ascending."""
    columns, rows = db.fetch_rows("users", order_by="name", order_dir="ASC")
    name_idx = columns.index("name")

    names = [row[name_idx] for row in rows]
    assert names == sorted(names)
    assert names[0] == "Alice"


def test_sorting_desc(db: DatabaseConnection) -> None:
    """Test sorting data descending."""
    columns, rows = db.fetch_rows("users", order_by="name", order_dir="DESC")
    name_idx = columns.index("name")

    names = [row[name_idx] for row in rows]
    assert names == sorted(names, reverse=True)
    assert names[0] == "Eve"


def test_sorting_numeric(db: DatabaseConnection) -> None:
    """Test sorting numeric column."""
    columns, rows = db.fetch_rows("users", order_by="age", order_dir="ASC")
    age_idx = columns.index("age")

    ages = [row[age_idx] for row in rows]
    assert ages == sorted(ages)
    assert ages[0] == 25  # Bob


def test_filter_where(db: DatabaseConnection) -> None:
    """Test filtering with WHERE clause."""
    columns, rows = db.fetch_rows("users", where="age >= 30")
    age_idx = columns.index("age")

    assert len(rows) == 3  # Alice (30), Charlie (35), Eve (32)
    for row in rows:
        assert row[age_idx] >= 30


def test_filter_with_string(db: DatabaseConnection) -> None:
    """Test filtering with string comparison."""
    columns, rows = db.fetch_rows("users", where="name LIKE 'A%'")
    name_idx = columns.index("name")

    assert len(rows) == 1
    assert rows[0][name_idx] == "Alice"


def test_combined_filter_and_sort(db: DatabaseConnection) -> None:
    """Test combining filter and sort."""
    columns, rows = db.fetch_rows(
        "users", where="age >= 28", order_by="age", order_dir="DESC"
    )
    age_idx = columns.index("age")

    assert len(rows) == 4  # Alice (30), Charlie (35), Eve (32), Diana (28)
    ages = [row[age_idx] for row in rows]
    assert ages == [35, 32, 30, 28]


def test_pagination_limit(db: DatabaseConnection) -> None:
    """Test pagination with limit."""
    _, rows = db.fetch_rows("users", limit=2)
    assert len(rows) == 2


def test_pagination_offset(db: DatabaseConnection) -> None:
    """Test pagination with offset."""
    columns, all_rows = db.fetch_rows("users", order_by="id", order_dir="ASC")
    _, offset_rows = db.fetch_rows("users", offset=2, order_by="id", order_dir="ASC")

    assert len(offset_rows) == 3
    assert offset_rows[0] == all_rows[2]


def test_null_values(db: DatabaseConnection) -> None:
    """Test handling of NULL values."""
    columns, rows = db.fetch_rows("posts")
    content_idx = columns.index("content")

    # Charlie's post has NULL content
    null_found = any(row[content_idx] is None for row in rows)
    assert null_found


def test_empty_table(db: DatabaseConnection) -> None:
    """Test loading empty table."""
    columns, rows = db.fetch_rows("empty_table")

    assert len(columns) == 2  # id, value
    assert len(rows) == 0


def test_windowing(large_db_path: Path) -> None:
    """Test windowed data loading."""
    db = DatabaseConnection(str(large_db_path))

    try:
        page_size = 100

        # Load first window
        _, window1 = db.fetch_rows("numbers", offset=0, limit=page_size)
        assert len(window1) == 100
        assert window1[0][0] == 1
        assert window1[-1][0] == 100

        # Load second window
        _, window2 = db.fetch_rows("numbers", offset=100, limit=page_size)
        assert len(window2) == 100
        assert window2[0][0] == 101
        assert window2[-1][0] == 200

    finally:
        db.close()


def test_binary_data(blob_db_path: Path) -> None:
    """Test handling of binary (BLOB) data."""
    from sqv.widgets.data_viewer import DataViewerTab

    db = DatabaseConnection(str(blob_db_path))

    try:
        _, rows = db.fetch_rows("blobs")
        assert len(rows) == 3

        # Test that binary data is returned as bytes
        assert isinstance(rows[0][2], bytes)
        assert isinstance(rows[1][2], bytes)
        assert isinstance(rows[2][2], bytes)

        # Test the _format_cell method handles binary data
        # Create a minimal DataViewerTab to test the method
        viewer = DataViewerTab(db)

        # Test NULL handling
        assert viewer._format_cell(None) == "NULL"

        # Test binary data formatting with hex preview
        assert viewer._format_cell(b"\x00\x01\x02\x03") == "<BLOB 4 bytes: 00 01 02 03>"
        assert viewer._format_cell(b"[test]") == "<BLOB 6 bytes: 5B 74 65 73 74 5D>"

        # Test large blob (shows first 8 bytes with ellipsis)
        large_blob = b"\xb4|\x05\x00\x11\x22\x33\x44\x55\x66" * 100
        result = viewer._format_cell(large_blob)
        assert result == "<BLOB 1,000 bytes: B4 7C 05 00 11 22 33 44...>"

        # Test Rich markup escaping in regular strings
        assert viewer._format_cell("[bold]text[/bold]") == r"\[bold]text\[/bold]"
        assert viewer._format_cell("normal text") == "normal text"

        # Test text truncation
        long_text = "x" * 200
        result = viewer._format_cell(long_text)
        assert len(result) == 103  # 100 chars + "..."
        assert result.endswith("...")

        # Short text should not be truncated
        short_text = "x" * 50
        assert viewer._format_cell(short_text) == short_text

    finally:
        db.close()
