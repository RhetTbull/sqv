"""Main Textual application for sqv."""

import sys

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane

from sqv.db import DatabaseConnection
from sqv.widgets import DataViewerTab, SQLTab, StructureTab


class SQVApp(App):
    """SQLite Viewer TUI Application."""

    TITLE = "sqv - SQLite Viewer"

    CSS = """
    #tabs {
        height: 1fr;
    }

    #tabs > ContentSwitcher {
        height: 1fr;
    }

    #tabs TabPane {
        padding: 0;
        height: 1fr;
    }

    StructureTab {
        height: 1fr;
    }

    DataViewerTab {
        height: 1fr;
    }

    SQLTab {
        height: 1fr;
    }

    /* Nested TabbedContent in SQLTab */
    SQLTab TabbedContent {
        height: 1fr;
    }

    SQLTab ContentSwitcher {
        height: 1fr;
    }

    SQLTab TabPane {
        height: 1fr;
    }

    QueryPane {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("d", "switch_tab('structure')", "Database Structure", show=True),
        Binding("b", "switch_tab('data')", "Browse Data", show=True),
        Binding("e", "switch_tab('sql')", "Execute SQL", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, db_path: str) -> None:
        super().__init__()
        self.db_path = db_path
        # Connect to database before compose() runs
        try:
            self.db = DatabaseConnection(db_path)
        except FileNotFoundError:
            print(f"Error: Database file not found: {db_path}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: Failed to open database: {e}", file=sys.stderr)
            sys.exit(1)

    def compose(self) -> ComposeResult:
        self.sub_title = self.db_path
        yield Header()
        with TabbedContent(id="tabs"):
            with TabPane("Database Structure", id="structure"):
                yield StructureTab(self.db)
            with TabPane("Browse Data", id="data"):
                yield DataViewerTab(self.db)
            with TabPane("Execute SQL", id="sql"):
                yield SQLTab(self.db)
        yield Footer()

    def action_switch_tab(self, tab_id: str) -> None:
        """Switch to specified tab."""
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = tab_id

    def on_unmount(self) -> None:
        """Clean up database connection."""
        if self.db:
            self.db.close()
