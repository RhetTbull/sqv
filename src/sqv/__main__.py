"""Entry point for sqv."""

import sys

from sqv.app import SQVApp


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: sqv <database.db>")
        sys.exit(1)

    db_path = sys.argv[1]
    app = SQVApp(db_path)
    app.run()


if __name__ == "__main__":
    main()
