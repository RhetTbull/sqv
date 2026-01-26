# sqv - SQLite Viewer TUI

A fast, lightweight SQLite database viewer TUI built with Python and Textual.

## Features

- **Structure Tab**: Browse tables, indices, views, and triggers with their SQL definitions
- **Data Tab**: View table data with sorting and filtering
- **SQL Tab**: Execute arbitrary SQL queries

## Screenshots

![sqv structure screenshot](https://raw.githubusercontent.com/RhetTbull/sqv/main/screenshots/structure_view.png)

![sqv data screenshot](https://raw.githubusercontent.com/RhetTbull/sqv/main/screenshots/data_view.png)

![sqv sql screenshot](https://raw.githubusercontent.com/RhetTbull/sqv/main/screenshots/sql_view.png)

![sqv sql screenshot](https://raw.githubusercontent.com/RhetTbull/sqv/main/screenshots/cell_view.png)

## Installation

I recommend installation with [uv](https://docs.astral.sh/uv/).

```bash
uv tool install sqv
```

Or to run without installing:

```bash
uv tool run sqv <database.db>
```

To install from source:

```bash
git clone git@github.com:RhetTbull/sqv.git
uv sync
```

## Usage

```bash
sqv <database.db>
```

## Key Bindings

| Key | Action |
|-----|--------|
| d | Go to Database Structure tab |
| b | Go to Browse Data tab |
| e | Go to Execute SQL tab |
| Ctrl+q | Quit |
| Ctrl+Enter | Execute SQL (in SQL tab) |
| ? | Show help |
