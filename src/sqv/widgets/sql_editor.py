"""SQL editor widgets for executing queries."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Static, TabbedContent, TabPane, TextArea

from sqv.db import DatabaseConnection

MAX_QUERIES = 5


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

    def compose(self) -> ComposeResult:
        yield TextArea(
            "SELECT * FROM sqlite_master LIMIT 10;",
            language="sql",
            id=f"sql-input-{self.query_id}",
        )
        yield DataTable(id=f"results-{self.query_id}")
        yield Static(
            "Ctrl+Enter to run | Ctrl+T to add query | Alt+1-5 to switch",
            id=f"status-{self.query_id}",
        )

    def on_mount(self) -> None:
        """Set up the results table."""
        table = self.query_one(f"#results-{self.query_id}", DataTable)
        table.cursor_type = "row"

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
        new_pane = TabPane(f"Query {self.query_count}", id=f"query-pane-{self.query_count}")
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
