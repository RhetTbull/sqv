"""SQL editor widgets for executing queries."""

import csv
import json
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

    QueryPane > Static {
        height: auto;
        padding: 0 1;
        background: $surface;
        color: $text-muted;
    }
    """

    def __init__(self, db: DatabaseConnection, query_id: int) -> None:
        super().__init__()
        self.db = db
        self.query_id = query_id
        self.last_columns: list[str] = []
        self.last_rows: list[tuple] = []

    def compose(self) -> ComposeResult:
        yield TextArea(
            "SELECT * FROM sqlite_master LIMIT 10;",
            language="sql",
            id=f"sql-input-{self.query_id}",
        )
        yield DataTable(id=f"results-{self.query_id}")
        yield Static(
            "Ctrl+Enter to run | Ctrl+E to export | Ctrl+T new query",
            id=f"status-{self.query_id}",
        )

    def on_mount(self) -> None:
        """Set up the results table."""
        table = self.query_one(f"#results-{self.query_id}", DataTable)
        table.cursor_type = "row"

    def _format_cell(self, value: object) -> str:
        """Format a cell value for display, handling binary data and escaping markup."""
        if value is None:
            return "NULL"
        if isinstance(value, bytes):
            preview_bytes = 8
            hex_preview = " ".join(f"{b:02X}" for b in value[:preview_bytes])
            ellipsis = "..." if len(value) > preview_bytes else ""
            return f"<BLOB {len(value):,} bytes: {hex_preview}{ellipsis}>"
        # Escape Rich markup characters to prevent parsing errors
        text = str(value)
        return text.replace("[", r"\[")

    def execute_sql(self) -> None:
        """Execute the SQL in this pane's input."""
        sql_input = self.query_one(f"#sql-input-{self.query_id}", TextArea)
        results_table = self.query_one(f"#results-{self.query_id}", DataTable)
        status = self.query_one(f"#status-{self.query_id}", Static)

        sql = sql_input.text.strip()
        if not sql:
            status.update("No SQL to execute")
            return

        try:
            columns, rows, elapsed = self.db.execute_sql(sql)

            # Store for export
            self.last_columns = columns
            self.last_rows = rows

            # Clear and populate results
            results_table.clear(columns=True)

            for col in columns:
                results_table.add_column(col, key=col)

            for row in rows:
                results_table.add_row(*[self._format_cell(v) for v in row])

            status.update(f"Success: {len(rows)} rows returned in {elapsed:.4f}s")

        except Exception as e:
            results_table.clear(columns=True)
            status.update(f"Error: {e}")

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
        tabs = self.query_one("#query-tabs", TabbedContent)
        new_pane = TabPane(
            f"Query {self.query_count}", id=f"query-pane-{self.query_count}"
        )
        new_pane.compose_add_child(QueryPane(self.db, self.query_count))
        tabs.add_pane(new_pane)
        tabs.active = f"query-pane-{self.query_count}"

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
        tabs = self.query_one("#query-tabs", TabbedContent)
        active_id = tabs.active
        if active_id:
            # Extract query number from pane id (e.g., "query-pane-1" -> 1)
            query_num = active_id.split("-")[-1]
            pane = self.query_one(f"#query-pane-{query_num}", TabPane)
            query_pane = pane.query_one(QueryPane)
            query_pane.execute_sql()
