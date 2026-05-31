"""Cell viewer modal for displaying full cell contents."""

import json
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, TextArea


class CellViewerScreen(ModalScreen[None]):
    """Modal screen for viewing full cell content."""

    UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
    MACOS_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)

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

    def _format_raw_value(self) -> tuple[bool, str]:
        """Format the raw value using the same rendering as the existing viewer."""
        if self.raw_value is None:
            return False, "NULL"
        elif isinstance(self.raw_value, bytes):
            # Show hex dump for binary data
            hex_lines = []
            data = self.raw_value
            for i in range(0, len(data), 16):
                chunk = data[i : i + 16]
                hex_part = " ".join(f"{b:02X}" for b in chunk)
                ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                hex_lines.append(f"{i:08X}  {hex_part:<48}  {ascii_part}")
            return False, f"BLOB ({len(data):,} bytes)\n\n" + "\n".join(hex_lines)
        else:
            display_value = str(self.raw_value)
            # Check if it's JSON
            return self._is_json(display_value)

    def _get_numeric_value(self) -> Decimal | None:
        """Return the value as a finite decimal if it is clearly numeric."""
        if not isinstance(self.raw_value, int | float) or isinstance(
            self.raw_value, bool
        ):
            return None

        number = Decimal(str(self.raw_value))
        if not number.is_finite():
            return None
        return number

    def _format_value_with_commas(self) -> str:
        """Format a numeric value with thousands separators."""
        number = self._get_numeric_value()
        if number is None:
            return "N/A (not numeric)"
        return f"{number:,f}"

    def _format_datetime_from_epoch(self, epoch: datetime) -> str:
        """Format the numeric value as a UTC date/time from the supplied epoch."""
        number = self._get_numeric_value()
        if number is None:
            return "N/A (not numeric)"

        try:
            seconds = float(number)
            if not math.isfinite(seconds):
                return "N/A (not numeric)"
            date_time = epoch + timedelta(seconds=seconds)
        except (OverflowError, ValueError):
            return "N/A (out of range)"

        return date_time.isoformat().replace("+00:00", "Z")

    def _build_display_value(self) -> str:
        """Build the complete text shown in the cell viewer."""
        _is_json, raw_value = self._format_raw_value()
        sections = [("Raw value", raw_value)]
        if self._get_numeric_value() is not None:
            sections.extend(
                [
                    ("Raw value with commas", self._format_value_with_commas()),
                    (
                        "Unix date/time (UTC)",
                        self._format_datetime_from_epoch(self.UNIX_EPOCH),
                    ),
                    (
                        "macOS date/time (UTC)",
                        self._format_datetime_from_epoch(self.MACOS_EPOCH),
                    ),
                ]
            )
        return "\n\n".join(f"{label}:\n{value}" for label, value in sections)

    def compose(self) -> ComposeResult:
        display_value = self._build_display_value()
        with Vertical():
            yield Label(f"Column: {self.column_name}")
            yield TextArea(display_value, read_only=True, id="cell-content")
            yield Label("Press Escape to close", classes="hint")

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)
