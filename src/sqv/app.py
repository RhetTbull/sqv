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
    TabbedContent {
        height: 1fr;
    }

    ContentSwitcher {
        height: 1fr;
    }

    TabPane {
        padding: 0;
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
    """

    BINDINGS = [
        Binding("0", "switch_tab('structure')", "Structure", show=True),
        Binding("1", "switch_tab('data')", "Data", show=True),
        Binding("2", "switch_tab('sql')", "SQL", show=True),
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
            with TabPane("Structure", id="structure"):
                yield StructureTab(self.db)
            with TabPane("Data", id="data"):
                yield DataViewerTab(self.db)
            with TabPane("SQL", id="sql"):
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
