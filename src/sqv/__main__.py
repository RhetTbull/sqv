"""Entry point for sqv."""

import argparse

from sqv import __version__
from sqv.app import SQVApp


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="sqv",
        description="A fast, lightweight SQLite database viewer TUI.",
        epilog="""
Key bindings:
  0, 1, 2      Switch between Structure, Data, and SQL tabs
  q            Quit
  Ctrl+Enter   Execute SQL query (in SQL tab)
  Ctrl+T       Add new query tab (in SQL tab)
  Ctrl+E       Export query results (in SQL tab)
  Ctrl+C       Copy query to clipboard (in SQL tab)
  Alt+1-5      Switch between query tabs (in SQL tab)

Examples:
  sqv mydata.db          Open mydata.db in the viewer
  sqv ~/Documents/app.db Open a database from home directory
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "database",
        metavar="DATABASE",
        help="Path to SQLite database file",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    app = SQVApp(args.database)
    app.run()


if __name__ == "__main__":
    main()
