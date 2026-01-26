"""Cell viewer modal for displaying full cell contents."""

import json

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, TextArea


class CellViewerScreen(ModalScreen[None]):
    """Modal screen for viewing full cell content."""

    DEFAULT_CSS = """
    CellViewerScreen {
        align: center middle;
    }

    CellViewerScreen > Vertical {
        width: 80%;
        height: 80%;
        padding: 1 2;
        background: $surface;
        border: solid $primary;
    }

    CellViewerScreen > Vertical > Label {
        padding: 0 0 1 0;
        text-style: bold;
    }

    CellViewerScreen > Vertical > TextArea {
        height: 1fr;
    }

    CellViewerScreen > Vertical > .hint {
        height: auto;
        padding: 1 0 0 0;
        color: $text-muted;
        text-style: italic;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]

    def __init__(self, column_name: str, value: object) -> None:
        super().__init__()
        self.column_name = column_name
        self.raw_value = value

    def _is_json(self, value: str) -> tuple[bool, str]:
        """Check if value is valid JSON and return formatted version."""
        try:
            parsed = json.loads(value)
            # Format with indentation for readability
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            return True, formatted
        except (json.JSONDecodeError, TypeError):
            return False, value

    def compose(self) -> ComposeResult:
        # Format the value for display
        is_json = False
        if self.raw_value is None:
            display_value = "NULL"
        elif isinstance(self.raw_value, bytes):
            # Show hex dump for binary data
            hex_lines = []
            data = self.raw_value
            for i in range(0, len(data), 16):
                chunk = data[i : i + 16]
                hex_part = " ".join(f"{b:02X}" for b in chunk)
                ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                hex_lines.append(f"{i:08X}  {hex_part:<48}  {ascii_part}")
            display_value = f"BLOB ({len(data):,} bytes)\n\n" + "\n".join(hex_lines)
        else:
            display_value = str(self.raw_value)
            # Check if it's JSON
            is_json, display_value = self._is_json(display_value)

        with Vertical():
            yield Label(f"Column: {self.column_name}")
            if is_json:
                yield TextArea(
                    display_value,
                    read_only=True,
                    language="json",
                    theme="monokai",
                    id="cell-content",
                )
            else:
                yield TextArea(display_value, read_only=True, id="cell-content")
            yield Label("Press Escape to close", classes="hint")

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)
