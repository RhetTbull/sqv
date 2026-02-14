# CLAUDE.md

## Project Overview

sqv is a fast, lightweight SQLite Viewer TUI built with Python and the Textual framework. It provides three main tabs: Database Structure, Browse Data, and Execute SQL.

## Commands

```bash
# Install dependencies
uv sync

# Run the app
uv run sqv <database.db>

# Run all tests
python -m pytest tests/ -v

# Lint
python -m ruff check src/ tests/

# Format
python -m ruff format src/ tests/
```

## Project Structure

- `src/sqv/` — Main source package
  - `app.py` — Main Textual app (SQVApp)
  - `db.py` — DatabaseConnection class (model layer)
  - `widgets/` — UI widgets: structure.py, data_viewer.py, sql_editor.py, cell_viewer.py
  - `__main__.py` — CLI entry point
- `tests/` — pytest test suite with async support (pytest-asyncio)
  - `conftest.py` — Shared fixtures (sample_db_path, blob_db_path, large_db_path)

## Code Conventions

- Python 3.11+ with type hints throughout
- Line length: 100 characters
- Ruff for linting/formatting (rules: E, F, I, UP, B, SIM)
- Textual framework patterns: CSS via `DEFAULT_CSS`, message-based communication, compose() for widget trees
- Private methods prefixed with `_`
- Dependencies managed with `uv`; single runtime dependency: `textual>=0.89.0`
- Version managed via bump2version (`.bumpversion.cfg`), tracked in `__init__.py` and `pyproject.toml`
