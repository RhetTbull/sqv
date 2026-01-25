"""SQL editor widgets for executing queries."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Button, DataTable, Static, TextArea

from sqv.db import DatabaseConnection


class SQLInput(TextArea):
    """Text area for SQL input with execution binding."""

    BINDINGS = [
        Binding("ctrl+enter", "execute", "Execute SQL", show=True),
    ]

    def __init__(self) -> None:
        super().__init__(language="sql", id="sql-input")
        self.text = "SELECT * FROM sqlite_master LIMIT 10;"


class SQLTab(Vertical):
    """SQL execution tab."""

    DEFAULT_CSS = """
    SQLTab {
        height: 100%;
    }

    SQLTab > SQLInput {
        height: 40%;
        border: solid $primary;
    }

    SQLTab > Vertical > Button {
        margin: 1;
        width: auto;
    }

    SQLTab > DataTable {
        height: 50%;
        border: solid $primary;
    }

    SQLTab > Static {
        height: auto;
        padding: 0 1;
        background: $surface;
    }
    """

    BINDINGS = [
        Binding("ctrl+enter", "execute_sql", "Execute SQL", show=True),
    ]

    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__()
        self.db = db

    def compose(self) -> ComposeResult:
        yield SQLInput()
        with Vertical():
            yield Button("Run (Ctrl+Enter)", id="run-button", variant="primary")
        yield DataTable(id="results-table")
        yield Static("Enter SQL and press Ctrl+Enter or click Run", id="sql-status")

    def on_mount(self) -> None:
        """Set up the results table."""
        table = self.query_one("#results-table", DataTable)
        table.cursor_type = "row"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle run button click."""
        if event.button.id == "run-button":
            self._execute_sql()

    def action_execute_sql(self) -> None:
        """Execute SQL action."""
        self._execute_sql()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text area changes - needed to keep focus working."""
        pass

    def _execute_sql(self) -> None:
        """Execute the SQL in the input."""
        sql_input = self.query_one("#sql-input", TextArea)
        results_table = self.query_one("#results-table", DataTable)
        status = self.query_one("#sql-status", Static)

        sql = sql_input.text.strip()
        if not sql:
            status.update("No SQL to execute")
            return

        try:
            columns, rows, elapsed = self.db.execute_sql(sql)

            # Clear and populate results
            results_table.clear(columns=True)

            for col in columns:
                results_table.add_column(col, key=col)

            for row in rows:
                results_table.add_row(*[str(v) if v is not None else "NULL" for v in row])

            status.update(f"Success: {len(rows)} rows returned in {elapsed:.4f}s")

        except Exception as e:
            results_table.clear(columns=True)
            status.update(f"Error: {e}")
