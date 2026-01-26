"""Data viewer widgets for browsing table contents."""

import time

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Select, Static

from sqv.db import DatabaseConnection
from sqv.widgets.cell_viewer import CellViewerScreen


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
        width: 40%;
    }

    DataViewerTab > Horizontal > Button {
        width: auto;
        min-width: 5;
    }

    DataViewerTab > Horizontal > #clear-filter {
        min-width: 3;
    }

    DataViewerTab > DataTable {
        height: 1fr;
        border: solid $primary;
    }

    DataViewerTab > #nav-bar {
        height: auto;
        padding: 0 1;
        align: center middle;
    }

    DataViewerTab > #nav-bar > Button {
        min-width: 8;
        margin: 0 1;
    }

    DataViewerTab > #nav-bar > Static {
        width: auto;
        padding: 0 2;
    }

    DataViewerTab > #status-bar {
        height: auto;
        padding: 0 1;
        color: $text-muted;
    }
    """

    PAGE_SIZE = 500

    BINDINGS = [
        Binding("pagedown", "next_page", "Next Page", show=False),
        Binding("pageup", "prev_page", "Prev Page", show=False),
        Binding("home", "first_page", "First Page", show=False),
        Binding("end", "last_page", "Last Page", show=False),
        Binding("enter", "view_cell", "View Cell", show=False),
    ]

    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__()
        self.db = db
        self.current_table: str | None = None
        self.current_offset = 0
        self.total_rows = 0
        self.filtered_count: int | None = None
        self.order_by: str | None = None
        self.order_dir = "ASC"
        self.where_clause: str | None = None
        self.columns: list[str] = []
        self.current_rows: list[tuple] = []  # Raw data for current page
        self._last_highlight: tuple[int, int, float] = (-1, -1, 0.0)  # row, col, time
        self._last_select: tuple[int, int, float] = (-1, -1, 0.0)  # row, col, time

    def compose(self) -> ComposeResult:
        tables = self.db.get_tables()
        options = [(t, t) for t in tables]

        with Horizontal():
            yield Select(options, prompt="Select table", id="table-select")
            yield Input(placeholder="WHERE clause (e.g., id > 10)", id="filter-input")
            yield Button("Apply", id="apply-filter")
            yield Button("✕", id="clear-filter", variant="error")

        yield DataTable(id="data-table")

        with Horizontal(id="nav-bar"):
            yield Button("◀◀", id="first-page", disabled=True)
            yield Button("◀ Prev", id="prev-page", disabled=True)
            yield Static("No data", id="page-info")
            yield Button("Next ▶", id="next-page", disabled=True)
            yield Button("▶▶", id="last-page", disabled=True)

        yield Static(
            "Select a table | PgUp/PgDn to navigate | Click column header to sort",
            id="status-bar",
        )

    def on_mount(self) -> None:
        """Set up the data table."""
        table = self.query_one("#data-table", DataTable)
        table.cursor_type = "cell"

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        """Track highlighted cell for Enter key detection."""
        self._last_highlight = (event.coordinate.row, event.coordinate.column, time.time())

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Handle cell selection - detect double-click or Enter on highlighted cell."""
        row_idx = event.coordinate.row
        col_idx = event.coordinate.column
        now = time.time()

        highlight_row, highlight_col, highlight_time = self._last_highlight
        select_row, select_col, select_time = self._last_select

        # Check for keyboard Enter: cell was highlighted > 100ms ago
        time_since_highlight = now - highlight_time
        if (row_idx == highlight_row and col_idx == highlight_col
                and time_since_highlight > 0.1):
            self._show_cell_viewer(row_idx, col_idx)
            self._last_select = (row_idx, col_idx, now)
            return

        # Check for mouse double-click: same cell selected within 500ms
        time_since_select = now - select_time
        if (row_idx == select_row and col_idx == select_col
                and time_since_select < 0.5):
            self._show_cell_viewer(row_idx, col_idx)

        # Track this selection for double-click detection
        self._last_select = (row_idx, col_idx, now)

    def _show_cell_viewer(self, row_idx: int, col_idx: int) -> None:
        """Show the cell viewer modal for the given cell."""
        if not self.current_rows or row_idx >= len(self.current_rows):
            return
        if not self.columns or col_idx >= len(self.columns):
            return

        column_name = self.columns[col_idx]
        value = self.current_rows[row_idx][col_idx]
        self.app.push_screen(CellViewerScreen(column_name, value))

    def action_view_cell(self) -> None:
        """View the currently selected cell in a popup."""
        table = self.query_one("#data-table", DataTable)
        if table.cursor_coordinate:
            row_idx = table.cursor_coordinate.row
            col_idx = table.cursor_coordinate.column
            self._show_cell_viewer(row_idx, col_idx)

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle table selection."""
        if event.select.id == "table-select" and event.value != Select.BLANK:
            self.current_table = str(event.value)
            self.current_offset = 0
            self.order_by = None
            self.order_dir = "ASC"
            self.where_clause = None
            self.filtered_count = None
            self.query_one("#filter-input", Input).value = ""
            self._load_data()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "apply-filter":
            self._apply_filter()
        elif event.button.id == "clear-filter":
            self._clear_filter()
        elif event.button.id == "next-page":
            self.action_next_page()
        elif event.button.id == "prev-page":
            self.action_prev_page()
        elif event.button.id == "first-page":
            self.action_first_page()
        elif event.button.id == "last-page":
            self.action_last_page()

    def _clear_filter(self) -> None:
        """Clear the WHERE filter."""
        filter_input = self.query_one("#filter-input", Input)
        filter_input.value = ""
        self.where_clause = None
        self.filtered_count = None
        self.current_offset = 0
        self._load_data()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in filter input."""
        if event.input.id == "filter-input":
            self._apply_filter()

    def _apply_filter(self) -> None:
        """Apply the WHERE filter."""
        filter_input = self.query_one("#filter-input", Input)
        where = filter_input.value.strip()
        self.where_clause = where if where else None
        self.filtered_count = None
        self.current_offset = 0
        self._load_data()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Handle column header click for sorting."""
        if not self.current_table:
            return

        column_key = event.column_key.value
        if self.order_by == column_key:
            self.order_dir = "DESC" if self.order_dir == "ASC" else "ASC"
        else:
            self.order_by = column_key
            self.order_dir = "ASC"

        self.current_offset = 0
        self._load_data()

    def _get_effective_count(self) -> int:
        """Get the count of rows considering filter."""
        if self.where_clause:
            if self.filtered_count is None:
                try:
                    _, rows, _ = self.db.execute_sql(
                        f"SELECT COUNT(*) FROM [{self.current_table}] WHERE {self.where_clause}"
                    )
                    self.filtered_count = rows[0][0]
                except Exception:
                    self.filtered_count = 0
            return self.filtered_count or 0
        return self.total_rows

    MAX_CELL_LENGTH = 120

    def _format_cell(self, value: object) -> str:
        """Format a cell value for display, handling binary data and escaping markup."""
        if value is None:
            return "NULL"
        if isinstance(value, bytes):
            preview_bytes = 8
            hex_preview = " ".join(f"{b:02X}" for b in value[:preview_bytes])
            ellipsis = "..." if len(value) > preview_bytes else ""
            return f"<BLOB {len(value):,} bytes: {hex_preview}{ellipsis}>"
        # Convert to string and truncate if too long
        text = str(value)
        if len(text) > self.MAX_CELL_LENGTH:
            text = text[: self.MAX_CELL_LENGTH] + "..."
        # Escape Rich markup characters to prevent parsing errors
        return text.replace("[", r"\[")

    def _load_data(self) -> None:
        """Load data from current table."""
        if not self.current_table:
            return

        table_widget = self.query_one("#data-table", DataTable)
        status = self.query_one("#status-bar", Static)
        page_info = self.query_one("#page-info", Static)

        try:
            self.total_rows = self.db.get_row_count(self.current_table)
            effective_count = self._get_effective_count()

            columns, rows = self.db.fetch_rows(
                self.current_table,
                offset=self.current_offset,
                limit=self.PAGE_SIZE,
                order_by=self.order_by,
                order_dir=self.order_dir,
                where=self.where_clause,
            )

            self.columns = columns
            self.current_rows = list(rows)  # Store raw data for cell viewer
            table_widget.clear(columns=True)

            for col in columns:
                label = col
                if col == self.order_by:
                    label = f"{col} {'↑' if self.order_dir == 'ASC' else '↓'}"
                table_widget.add_column(label, key=col)

            for row in rows:
                table_widget.add_row(*[self._format_cell(v) for v in row])

            loaded = len(rows)
            start = self.current_offset + 1 if loaded > 0 else 0
            end = self.current_offset + loaded

            if effective_count > 0:
                page_info.update(f"Rows {start:,}-{end:,} of {effective_count:,}")
            else:
                page_info.update("No matching rows")

            self._update_nav_buttons(effective_count)

            parts = [f"Table: {self.current_table}"]
            if self.where_clause:
                parts.append(f"Filter: {self.where_clause}")
            if self.order_by:
                parts.append(f"Sort: {self.order_by} {self.order_dir}")
            parts.append("PgUp/PgDn to navigate")
            status.update(" | ".join(parts))

        except Exception as e:
            status.update(f"Error: {e}")
            page_info.update("Error")
            table_widget.clear(columns=True)
            self._update_nav_buttons(0)

    def _update_nav_buttons(self, effective_count: int) -> None:
        """Update navigation button states."""
        has_prev = self.current_offset > 0
        has_next = self.current_offset + self.PAGE_SIZE < effective_count

        self.query_one("#first-page", Button).disabled = not has_prev
        self.query_one("#prev-page", Button).disabled = not has_prev
        self.query_one("#next-page", Button).disabled = not has_next
        self.query_one("#last-page", Button).disabled = not has_next

    def action_next_page(self) -> None:
        """Load next page of data."""
        if not self.current_table:
            return
        effective_count = self._get_effective_count()
        if self.current_offset + self.PAGE_SIZE < effective_count:
            self.current_offset += self.PAGE_SIZE
            self._load_data()

    def action_prev_page(self) -> None:
        """Load previous page of data."""
        if self.current_table and self.current_offset > 0:
            self.current_offset = max(0, self.current_offset - self.PAGE_SIZE)
            self._load_data()

    def action_first_page(self) -> None:
        """Go to first page."""
        if self.current_table and self.current_offset > 0:
            self.current_offset = 0
            self._load_data()

    def action_last_page(self) -> None:
        """Go to last page."""
        if not self.current_table:
            return
        effective_count = self._get_effective_count()
        if effective_count > self.PAGE_SIZE:
            self.current_offset = (
                (effective_count - 1) // self.PAGE_SIZE
            ) * self.PAGE_SIZE
            self._load_data()
