"""SQL editor widgets for executing queries."""

import csv
import json
import time
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)

from sqv.db import DatabaseConnection
from sqv.widgets.cell_viewer import CellViewerScreen

MAX_QUERIES = 5


class ExportScreen(ModalScreen[tuple[str, str] | None]):
    """Modal screen for export options."""

    DEFAULT_CSS = """
    ExportScreen {
        align: center middle;
    }

    ExportScreen > Vertical {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: solid $primary;
    }

    ExportScreen > Vertical > Label {
        padding: 1 0;
    }

    ExportScreen > Vertical > Input {
        margin-bottom: 1;
    }

    ExportScreen > Vertical > Select {
        margin-bottom: 1;
    }

    ExportScreen > Vertical > Horizontal {
        height: auto;
        align: right middle;
    }

    ExportScreen > Vertical > Horizontal > Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Export Results")
            yield Label("Format:")
            yield Select(
                [("CSV", "csv"), ("JSON", "json")],
                value="csv",
                id="export-format",
            )
            yield Label("Filename:")
            yield Input(placeholder="export.csv", id="export-filename")
            with Horizontal():
                yield Button("Cancel", id="cancel")
                yield Button("Export", id="export", variant="primary")

    def on_mount(self) -> None:
        """Focus the filename input."""
        self.query_one("#export-filename", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "export":
            self._do_export()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in filename input."""
        self._do_export()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Update filename extension when format changes."""
        filename_input = self.query_one("#export-filename", Input)
        current = filename_input.value
        new_ext = f".{event.value}"

        if current:
            path = Path(current)
            if path.suffix in (".csv", ".json"):
                filename_input.value = str(path.with_suffix(new_ext))
        else:
            filename_input.value = f"export{new_ext}"

    def _do_export(self) -> None:
        """Perform the export."""
        format_select = self.query_one("#export-format", Select)
        filename_input = self.query_one("#export-filename", Input)

        fmt = str(format_select.value)
        filename = filename_input.value.strip()

        if not filename:
            filename = f"export.{fmt}"

        self.dismiss((fmt, filename))

    def action_cancel(self) -> None:
        """Cancel export."""
        self.dismiss(None)


class QueryPane(Vertical):
    """A single query pane with SQL input, results, and status."""

    DEFAULT_CSS = """
    QueryPane {
        height: 1fr;
    }

    QueryPane > TextArea {
        height: 35%;
        border: solid $primary;
    }

    QueryPane > DataTable {
        height: 1fr;
        border: solid $primary;
    }

    QueryPane > #nav-bar {
        height: auto;
        padding: 0 1;
        align: center middle;
    }

    QueryPane > #nav-bar > Button {
        min-width: 8;
        margin: 0 1;
    }

    QueryPane > #nav-bar > Static {
        width: auto;
        padding: 0 2;
    }

    QueryPane > Static.status {
        height: auto;
        padding: 0 1;
        background: $surface;
        color: $text-muted;
    }
    """

    PAGE_SIZE = 500

    def __init__(self, db: DatabaseConnection, query_id: int) -> None:
        super().__init__()
        self.db = db
        self.query_id = query_id
        self.last_columns: list[str] = []
        self.last_rows: list[tuple] = []
        self.current_offset = 0
        self._last_highlight: tuple[int, int, float] = (-1, -1, 0.0)  # row, col, time
        self._last_select: tuple[int, int, float] = (-1, -1, 0.0)  # row, col, time

    def compose(self) -> ComposeResult:
        yield TextArea(
            "",
            language="sql",
            theme="monokai",
            id=f"sql-input-{self.query_id}",
        )
        yield DataTable(id=f"results-{self.query_id}")
        with Horizontal(id="nav-bar"):
            yield Button("◀◀", id="first-page", disabled=True)
            yield Button("◀ Prev", id="prev-page", disabled=True)
            yield Static("No results", id="page-info")
            yield Button("Next ▶", id="next-page", disabled=True)
            yield Button("▶▶", id="last-page", disabled=True)
        yield Static(
            "Ctrl+Enter to run | Ctrl+E to export | PgUp/PgDn to navigate",
            id=f"status-{self.query_id}",
            classes="status",
        )

    def on_mount(self) -> None:
        """Set up the results table."""
        table = self.query_one(f"#results-{self.query_id}", DataTable)
        table.cursor_type = "cell"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle navigation button clicks."""
        if event.button.id == "next-page":
            self._next_page()
        elif event.button.id == "prev-page":
            self._prev_page()
        elif event.button.id == "first-page":
            self._first_page()
        elif event.button.id == "last-page":
            self._last_page()

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        """Track highlighted cell for Enter key detection."""
        self._last_highlight = (
            event.coordinate.row,
            event.coordinate.column,
            time.time(),
        )

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Handle cell selection - detect double-click or Enter on highlighted cell."""
        row_idx = event.coordinate.row
        col_idx = event.coordinate.column
        now = time.time()

        highlight_row, highlight_col, highlight_time = self._last_highlight
        select_row, select_col, select_time = self._last_select

        # Check for keyboard Enter: cell was highlighted > 100ms ago
        time_since_highlight = now - highlight_time
        if (
            row_idx == highlight_row
            and col_idx == highlight_col
            and time_since_highlight > 0.1
        ):
            self._show_cell_viewer(row_idx, col_idx)
            self._last_select = (row_idx, col_idx, now)
            return

        # Check for mouse double-click: same cell selected within 500ms
        time_since_select = now - select_time
        if row_idx == select_row and col_idx == select_col and time_since_select < 0.5:
            self._show_cell_viewer(row_idx, col_idx)

        # Track this selection for double-click detection
        self._last_select = (row_idx, col_idx, now)

    def _show_cell_viewer(self, row_idx: int, col_idx: int) -> None:
        """Show the cell viewer modal for the given cell."""
        # Calculate actual row index in the full result set
        actual_row_idx = self.current_offset + row_idx

        if not self.last_rows or actual_row_idx >= len(self.last_rows):
            return
        if not self.last_columns or col_idx >= len(self.last_columns):
            return

        column_name = self.last_columns[col_idx]
        value = self.last_rows[actual_row_idx][col_idx]
        self.app.push_screen(CellViewerScreen(column_name, value))

    def view_current_cell(self) -> None:
        """View the currently selected cell in a popup."""
        table = self.query_one(f"#results-{self.query_id}", DataTable)
        if table.cursor_coordinate:
            row_idx = table.cursor_coordinate.row
            col_idx = table.cursor_coordinate.column
            self._show_cell_viewer(row_idx, col_idx)

    MAX_CELL_LENGTH = 100

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

    def execute_sql(self) -> None:
        """Execute the SQL in this pane's input."""
        sql_input = self.query_one(f"#sql-input-{self.query_id}", TextArea)
        status = self.query_one(f"#status-{self.query_id}", Static)

        sql = sql_input.text.strip()
        if not sql:
            status.update("No SQL to execute")
            return

        try:
            columns, rows, elapsed = self.db.execute_sql(sql)

            # Store for export and pagination
            self.last_columns = columns
            self.last_rows = rows
            self.current_offset = 0

            # Display first page
            self._display_current_page()

            status.update(f"Success: {len(rows):,} rows returned in {elapsed:.4f}s")

        except Exception as e:
            results_table = self.query_one(f"#results-{self.query_id}", DataTable)
            results_table.clear(columns=True)
            self._update_nav_buttons()
            status.update(f"Error: {e}")

    def _display_current_page(self) -> None:
        """Display the current page of results."""
        results_table = self.query_one(f"#results-{self.query_id}", DataTable)
        page_info = self.query_one("#page-info", Static)

        results_table.clear(columns=True)

        if not self.last_columns:
            page_info.update("No results")
            self._update_nav_buttons()
            return

        for col in self.last_columns:
            results_table.add_column(col, key=col)

        # Get current page slice
        start = self.current_offset
        end = min(start + self.PAGE_SIZE, len(self.last_rows))
        page_rows = self.last_rows[start:end]

        for row in page_rows:
            results_table.add_row(*[self._format_cell(v) for v in row])

        # Force immediate column width calculation
        results_table.refresh()

        # Update page info
        total = len(self.last_rows)
        if total > 0:
            page_info.update(f"Rows {start + 1:,}-{end:,} of {total:,}")
        else:
            page_info.update("No results")

        self._update_nav_buttons()

    def _update_nav_buttons(self) -> None:
        """Update navigation button states."""
        total = len(self.last_rows)
        has_prev = self.current_offset > 0
        has_next = self.current_offset + self.PAGE_SIZE < total

        self.query_one("#first-page", Button).disabled = not has_prev
        self.query_one("#prev-page", Button).disabled = not has_prev
        self.query_one("#next-page", Button).disabled = not has_next
        self.query_one("#last-page", Button).disabled = not has_next

    def _next_page(self) -> None:
        """Go to next page."""
        if self.current_offset + self.PAGE_SIZE < len(self.last_rows):
            self.current_offset += self.PAGE_SIZE
            self._display_current_page()

    def _prev_page(self) -> None:
        """Go to previous page."""
        if self.current_offset > 0:
            self.current_offset = max(0, self.current_offset - self.PAGE_SIZE)
            self._display_current_page()

    def _first_page(self) -> None:
        """Go to first page."""
        if self.current_offset > 0:
            self.current_offset = 0
            self._display_current_page()

    def _last_page(self) -> None:
        """Go to last page."""
        total = len(self.last_rows)
        if total > self.PAGE_SIZE:
            self.current_offset = ((total - 1) // self.PAGE_SIZE) * self.PAGE_SIZE
            self._display_current_page()

    def export_results(self, fmt: str, filename: str) -> str | None:
        """Export results to file. Returns error message or None on success."""
        if not self.last_columns or not self.last_rows:
            return "No results to export"

        try:
            path = Path(filename).expanduser()

            if fmt == "csv":
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(self.last_columns)
                    writer.writerows(self.last_rows)
            elif fmt == "json":
                data = [
                    dict(zip(self.last_columns, row, strict=False))
                    for row in self.last_rows
                ]
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
            else:
                return f"Unknown format: {fmt}"

            return None

        except Exception as e:
            return str(e)


class SQLTab(Vertical):
    """SQL execution tab with multiple query panes."""

    DEFAULT_CSS = """
    SQLTab {
        height: 1fr;
    }

    SQLTab > #query-tabs {
        height: 1fr;
    }

    SQLTab #query-tabs > ContentSwitcher {
        height: 1fr;
    }

    SQLTab #query-tabs TabPane {
        height: 1fr;
        padding: 0;
    }

    SQLTab #query-tabs TabPane > * {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("ctrl+enter", "execute_sql", "Execute", show=True),
        Binding("ctrl+t", "add_query", "+Query", show=True),
        Binding("ctrl+e", "export", "Export", show=True),
        Binding("ctrl+c", "copy_query", "Copy", show=False),
        Binding("alt+1", "switch_query(1)", "Q1", show=False),
        Binding("alt+2", "switch_query(2)", "Q2", show=False),
        Binding("alt+3", "switch_query(3)", "Q3", show=False),
        Binding("alt+4", "switch_query(4)", "Q4", show=False),
        Binding("alt+5", "switch_query(5)", "Q5", show=False),
        Binding("pagedown", "next_page", "Next Page", show=False),
        Binding("pageup", "prev_page", "Prev Page", show=False),
        Binding("home", "first_page", "First Page", show=False),
        Binding("end", "last_page", "Last Page", show=False),
        Binding("enter", "view_cell", "View Cell", show=False),
    ]

    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__()
        self.db = db
        self.query_count = 1

    def compose(self) -> ComposeResult:
        with TabbedContent(id="query-tabs"), TabPane("Query 1", id="query-pane-1"):
            yield QueryPane(self.db, 1)

    def action_add_query(self) -> None:
        """Add a new query pane."""
        self._add_query()

    def _add_query(self) -> None:
        """Add a new query tab."""
        if self.query_count >= MAX_QUERIES:
            self.notify(f"Maximum of {MAX_QUERIES} queries reached", severity="warning")
            return

        self.query_count += 1
        query_id = self.query_count
        tabs = self.query_one("#query-tabs", TabbedContent)
        new_pane = TabPane(f"Query {query_id}", id=f"query-pane-{query_id}")
        new_pane.compose_add_child(QueryPane(self.db, query_id))
        tabs.add_pane(new_pane)
        tabs.active = f"query-pane-{query_id}"

        # Focus the new query's TextArea after it's mounted
        def focus_new_input() -> None:
            try:
                pane = self.query_one(f"#query-pane-{query_id}", TabPane)
                sql_input = pane.query_one(f"#sql-input-{query_id}", TextArea)
                sql_input.focus()
            except Exception:
                pass

        self.call_later(focus_new_input)

    def action_switch_query(self, query_num: int) -> None:
        """Switch to a specific query tab."""
        if query_num > self.query_count:
            return
        tabs = self.query_one("#query-tabs", TabbedContent)
        tabs.active = f"query-pane-{query_num}"

    def action_copy_query(self) -> None:
        """Copy the current query to clipboard."""
        tabs = self.query_one("#query-tabs", TabbedContent)
        active_id = tabs.active
        if active_id:
            query_num = active_id.split("-")[-1]
            pane = self.query_one(f"#query-pane-{query_num}", TabPane)
            sql_input = pane.query_one(f"#sql-input-{query_num}", TextArea)
            sql = sql_input.text
            if sql:
                self.app.copy_to_clipboard(sql)
                self.notify("Query copied to clipboard", severity="information")

    def action_export(self) -> None:
        """Show export dialog."""
        self.app.push_screen(ExportScreen(), self._handle_export)

    def _handle_export(self, result: tuple[str, str] | None) -> None:
        """Handle export dialog result."""
        if result is None:
            return

        fmt, filename = result
        tabs = self.query_one("#query-tabs", TabbedContent)
        active_id = tabs.active
        if active_id:
            query_num = active_id.split("-")[-1]
            pane = self.query_one(f"#query-pane-{query_num}", TabPane)
            query_pane = pane.query_one(QueryPane)
            error = query_pane.export_results(fmt, filename)
            if error:
                self.notify(f"Export failed: {error}", severity="error")
            else:
                self.notify(f"Exported to {filename}", severity="information")

    def action_execute_sql(self) -> None:
        """Execute SQL in the active query pane."""
        query_pane = self._get_active_query_pane()
        if query_pane:
            query_pane.execute_sql()

    def _get_active_query_pane(self) -> QueryPane | None:
        """Get the active QueryPane."""
        tabs = self.query_one("#query-tabs", TabbedContent)
        active_id = tabs.active
        if active_id:
            query_num = active_id.split("-")[-1]
            pane = self.query_one(f"#query-pane-{query_num}", TabPane)
            return pane.query_one(QueryPane)
        return None

    def action_next_page(self) -> None:
        """Go to next page of results."""
        query_pane = self._get_active_query_pane()
        if query_pane:
            query_pane._next_page()

    def action_prev_page(self) -> None:
        """Go to previous page of results."""
        query_pane = self._get_active_query_pane()
        if query_pane:
            query_pane._prev_page()

    def action_first_page(self) -> None:
        """Go to first page of results."""
        query_pane = self._get_active_query_pane()
        if query_pane:
            query_pane._first_page()

    def action_last_page(self) -> None:
        """Go to last page of results."""
        query_pane = self._get_active_query_pane()
        if query_pane:
            query_pane._last_page()

    def action_view_cell(self) -> None:
        """View the currently selected cell in a popup."""
        query_pane = self._get_active_query_pane()
        if query_pane:
            query_pane.view_current_cell()

    def focus_input(self) -> None:
        """Focus the SQL input of the active query pane."""
        query_pane = self._get_active_query_pane()
        if query_pane:
            sql_input = query_pane.query_one(
                f"#sql-input-{query_pane.query_id}", TextArea
            )
            sql_input.focus()
