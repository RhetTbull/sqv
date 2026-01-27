# sqv - SQLite Viewer TUI

A fast, lightweight SQLite database viewer TUI built with Python and Textual.

## Features

- **Database Structure Tab**: Browse tables, indices, views, and triggers with their SQL definitions
- **Data Tab**: View table data with sorting and filtering
- **Execute SQL Query Tab**: Execute arbitrary SQL queries

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

## See Also

sqv is not intended to be a full SQL IDE. I built it to do exactly the things I wanted and nothing else. If you find sqv doesn't suit your needs, you might find one of these more full featured alternatives does:

* [harlequin](https://github.com/tconbeer/harlequin): The SQL IDE for your terminal
* [sqlit](https://github.com/Maxteabag/sqlit): A user friendly TUI for SQL databases. Written in python. Supports SQL server, Mysql, PostreSQL, SQLite, Turso and more.
* [litecli](https://github.com/dbcli/litecli): CLI for SQLite Databases with auto-completion and syntax highlighting
