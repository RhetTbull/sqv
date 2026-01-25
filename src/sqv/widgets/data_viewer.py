"""Data viewer widgets for browsing table contents."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Select, Static

from sqv.db import DatabaseConnection


class DataViewerTab(Vertical):
    """Data viewer tab for browsing table data."""

    DEFAULT_CSS = """
    DataViewerTab {
        height: 100%;
    }

    DataViewerTab > Horizontal {
        height: auto;
        padding: 1;
    }

    DataViewerTab > Horizontal > Select {
        width: 30%;
    }

    DataViewerTab > Horizontal > Input {
        width: 50%;
    }

    DataViewerTab > Horizontal > Button {
        width: auto;
    }

    DataViewerTab > DataTable {
        height: 1fr;
        border: solid $primary;
    }

    DataViewerTab > Static {
        height: auto;
        padding: 0 1;
    }
    """

    PAGE_SIZE = 100

    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__()
        self.db = db
        self.current_table: str | None = None
        self.current_offset = 0
        self.total_rows = 0
        self.order_by: str | None = None
        self.order_dir = "ASC"
        self.where_clause: str | None = None

    def compose(self) -> ComposeResult:
        tables = self.db.get_tables()
        options = [(t, t) for t in tables]

        with Horizontal():
            yield Select(options, prompt="Select table", id="table-select")
            yield Input(placeholder="WHERE clause (e.g., id > 10)", id="filter-input")
            yield Button("Apply", id="apply-filter")

        yield DataTable(id="data-table")
        yield Static("Select a table to view data", id="status-bar")

    def on_mount(self) -> None:
        """Set up the data table."""
        table = self.query_one("#data-table", DataTable)
        table.cursor_type = "row"

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle table selection."""
        if event.select.id == "table-select" and event.value != Select.BLANK:
            self.current_table = str(event.value)
            self.current_offset = 0
            self.order_by = None
            self.order_dir = "ASC"
            self.where_clause = None
            self.query_one("#filter-input", Input).value = ""
            self._load_data()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "apply-filter":
            self._apply_filter()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in filter input."""
        if event.input.id == "filter-input":
            self._apply_filter()

    def _apply_filter(self) -> None:
        """Apply the WHERE filter."""
        filter_input = self.query_one("#filter-input", Input)
        where = filter_input.value.strip()
        self.where_clause = where if where else None
        self.current_offset = 0
        self._load_data()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Handle column header click for sorting."""
        if not self.current_table:
            return

        column_key = str(event.column_key)
        if self.order_by == column_key:
            # Toggle direction
            self.order_dir = "DESC" if self.order_dir == "ASC" else "ASC"
        else:
            self.order_by = column_key
            self.order_dir = "ASC"

        self.current_offset = 0
        self._load_data()

    def _load_data(self) -> None:
        """Load data from current table."""
        if not self.current_table:
            return

        table_widget = self.query_one("#data-table", DataTable)
        status = self.query_one("#status-bar", Static)

        try:
            # Get total count
            self.total_rows = self.db.get_row_count(self.current_table)

            # Fetch rows
            columns, rows = self.db.fetch_rows(
                self.current_table,
                offset=self.current_offset,
                limit=self.PAGE_SIZE,
                order_by=self.order_by,
                order_dir=self.order_dir,
                where=self.where_clause,
            )

            # Clear and repopulate table
            table_widget.clear(columns=True)

            # Add columns with sort indicator
            for col in columns:
                label = col
                if col == self.order_by:
                    label = f"{col} {'↑' if self.order_dir == 'ASC' else '↓'}"
                table_widget.add_column(label, key=col)

            # Add rows
            for row in rows:
                table_widget.add_row(*[str(v) if v is not None else "NULL" for v in row])

            # Update status
            loaded = len(rows)
            where_str = f" (filtered: {self.where_clause})" if self.where_clause else ""
            order_str = f" ORDER BY {self.order_by} {self.order_dir}" if self.order_by else ""
            msg = f"Table: {self.current_table} | Showing {loaded} of {self.total_rows} rows"
            status.update(f"{msg}{where_str}{order_str}")

        except Exception as e:
            status.update(f"Error: {e}")
            table_widget.clear(columns=True)

    def action_next_page(self) -> None:
        """Load next page of data."""
        if self.current_table and self.current_offset + self.PAGE_SIZE < self.total_rows:
            self.current_offset += self.PAGE_SIZE
            self._load_data()

    def action_prev_page(self) -> None:
        """Load previous page of data."""
        if self.current_table and self.current_offset > 0:
            self.current_offset = max(0, self.current_offset - self.PAGE_SIZE)
            self._load_data()
