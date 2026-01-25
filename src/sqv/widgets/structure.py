"""Structure viewer widgets for displaying database schema."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Static, Tree

from sqv.db import DatabaseConnection


class StructureTree(Tree):
    """Tree widget showing database structure."""

    class ObjectSelected(Message):
        """Message sent when a database object is selected."""

        def __init__(self, object_type: str, name: str) -> None:
            self.object_type = object_type
            self.name = name
            super().__init__()

    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__("Database")
        self.db = db

    def on_mount(self) -> None:
        """Populate tree when mounted."""
        self.root.expand()
        self._populate_tree()

    def _populate_tree(self) -> None:
        """Populate the tree with database objects."""
        # Tables
        tables_node = self.root.add("Tables", expand=True)
        for table in self.db.get_tables():
            table_node = tables_node.add(table, data=("table", table))
            # Add columns as children
            for col_name, col_type, notnull, default in self.db.get_columns(table):
                null_str = " NOT NULL" if notnull else ""
                default_str = f" DEFAULT {default}" if default else ""
                table_node.add_leaf(
                    f"{col_name}: {col_type}{null_str}{default_str}",
                    data=("column", f"{table}.{col_name}"),
                )

        # Indices
        indices_node = self.root.add("Indices")
        for index in self.db.get_indices():
            indices_node.add_leaf(index, data=("index", index))

        # Views
        views_node = self.root.add("Views")
        for view in self.db.get_views():
            views_node.add_leaf(view, data=("view", view))

        # Triggers
        triggers_node = self.root.add("Triggers")
        for trigger in self.db.get_triggers():
            triggers_node.add_leaf(trigger, data=("trigger", trigger))

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection."""
        if event.node.data:
            object_type, name = event.node.data
            self.post_message(self.ObjectSelected(object_type, name))


class StructureDetail(Static):
    """Widget showing details of selected database object."""

    DEFAULT_CSS = """
    StructureDetail {
        padding: 1;
        border: solid $primary;
        height: 100%;
    }
    """

    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__("Select an object to view its definition")
        self.db = db

    def show_object(self, object_type: str, name: str) -> None:
        """Display details for the selected object."""
        if object_type == "column":
            # Column selected - show table SQL
            table_name = name.split(".")[0]
            sql = self.db.get_table_sql(table_name)
            self.update(f"-- Column from table: {table_name}\n\n{sql}")
        elif object_type in ("table", "view", "index", "trigger"):
            sql = self.db.get_table_sql(name)
            if sql:
                self.update(sql)
            else:
                self.update(f"No SQL definition available for {name}")
        else:
            self.update(f"Selected: {object_type} - {name}")


class StructureTab(Horizontal):
    """Structure tab container with tree and detail panes."""

    DEFAULT_CSS = """
    StructureTab {
        height: 100%;
    }

    StructureTab > StructureTree {
        width: 30%;
        border: solid $primary;
    }

    StructureTab > StructureDetail {
        width: 70%;
    }
    """

    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__()
        self.db = db

    def compose(self) -> ComposeResult:
        yield StructureTree(self.db)
        yield StructureDetail(self.db)

    def on_structure_tree_object_selected(
        self, event: StructureTree.ObjectSelected
    ) -> None:
        """Update detail pane when object is selected."""
        detail = self.query_one(StructureDetail)
        detail.show_object(event.object_type, event.name)
