"""Main Textual application for sqv."""

import sys

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Static, TabbedContent, TabPane

from sqv import __version__
from sqv.db import DatabaseConnection
from sqv.widgets import DataViewerTab, SQLTab, StructureTab

HELP_TEXT = """\
[b]sqv - SQLite Viewer[/b]  v{version}

[b u]Navigation[/b u]
  [b]d[/b]          Database Structure tab
  [b]b[/b]          Browse Data tab
  [b]e[/b]          Execute SQL tab
  [b]Ctrl+Q[/b]     Quit

[b u]Browse Data Tab[/b u]
  [b]PgUp/PgDn[/b]  Navigate pages
  [b]Home/End[/b]   First/last page
  [b]Enter[/b]      View cell contents
  [b]↑↓←→[/b]       Navigate cells
  Click column header to sort

[b u]Execute SQL Tab[/b u]
  [b]Ctrl+Enter[/b] Execute query
  [b]Ctrl+T[/b]     New query tab
  [b]Ctrl+E[/b]     Export results
  [b]Ctrl+C[/b]     Copy query to clipboard
  [b]Alt+1-5[/b]    Switch query tabs
  [b]PgUp/PgDn[/b]  Navigate result pages
  [b]Enter[/b]      View cell contents

[b u]Cell Viewer[/b u]
  [b]Escape[/b]     Close viewer

[dim]Press Escape or ? to close this help[/dim]
"""


class HelpScreen(ModalScreen[None]):
    """Modal screen showing help information."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }

    HelpScreen > Vertical {
        width: 60;
        height: auto;
        max-height: 80%;
        padding: 1 2;
        background: $surface;
        border: solid $primary;
    }

    HelpScreen > Vertical > Static {
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("question_mark", "close", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(HELP_TEXT.format(version=__version__))

    def action_close(self) -> None:
        """Close the help screen."""
        self.dismiss(None)


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
        Binding("question_mark", "show_help", "Help", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
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
            with TabPane("[u]D[/u]atabase Structure", id="structure"):
                yield StructureTab(self.db)
            with TabPane("[u]B[/u]rowse Data", id="data"):
                yield DataViewerTab(self.db)
            with TabPane("[u]E[/u]xecute SQL", id="sql"):
                yield SQLTab(self.db)
        yield Footer()

    def action_switch_tab(self, tab_id: str) -> None:
        """Switch to specified tab."""
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = tab_id

    def action_show_help(self) -> None:
        """Show the help screen."""
        self.push_screen(HelpScreen())

    def on_tabbed_content_tab_activated(
        self, event: TabbedContent.TabActivated
    ) -> None:
        """Handle tab activation to focus appropriate widget."""
        if event.pane.id == "sql":
            # Focus the SQL input when switching to Execute SQL tab
            sql_tab = self.query_one(SQLTab)
            self.call_later(sql_tab.focus_input)

    def on_unmount(self) -> None:
        """Clean up database connection."""
        if self.db:
            self.db.close()
