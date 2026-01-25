# sqv - SQLite Viewer TUI

A fast, lightweight SQLite database viewer TUI built with Python and Textual.

## Features

- **Structure Tab**: Browse tables, indices, views, and triggers with their SQL definitions
- **Data Tab**: View table data with sorting and filtering
- **SQL Tab**: Execute arbitrary SQL queries

## Installation

```bash
uv sync
```

## Usage

```bash
uv run sqv <database.db>
```

## Key Bindings

| Key | Action |
|-----|--------|
| 0 | Go to Structure tab |
| 1 | Go to Data tab |
| 2 | Go to SQL tab |
| q | Quit |
| Ctrl+Enter | Execute SQL (in SQL tab) |
