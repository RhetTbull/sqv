# sqv - SQLite Viewer TUI

A fast, lightweight SQLite database viewer TUI built with Python and Textual.

## Features

- **Structure Tab**: Browse tables, indices, views, and triggers with their SQL definitions
- **Data Tab**: View table data with sorting and filtering
- **SQL Tab**: Execute arbitrary SQL queries

## Installation

I recommend installation with [uv](https://docs.astral.sh/uv/).

```bash
uv tool install sqv
```

Or to run without installing:

```bash
uv tool run sqv
```

To install from source:

```bash
git clone git@github.com:RhetTbull/sqv.git
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
