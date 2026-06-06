"""Cell viewer modal for displaying full cell contents."""

import json
import math
import plistlib
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
        Binding("p", "toggle_plist", "Toggle Plist", show=False),
    ]

    def __init__(self, column_name: str, value: object) -> None:
        super().__init__()
        self.column_name = column_name
        self.raw_value = value
        self._show_decoded_plist = False

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
            return False, self._format_hex_dump(self.raw_value)
        else:
            display_value = str(self.raw_value)
            # Check if it's JSON
            return self._is_json(display_value)

    def _is_binary_plist(self) -> bool:
        """Return whether the raw value is a binary property list blob."""
        return isinstance(self.raw_value, bytes) and self.raw_value.startswith(b"bplist00")

    def _format_blob_preview(self, value: bytes) -> str:
        """Format a compact preview for nested plist bytes values."""
        preview_bytes = 16
        hex_preview = " ".join(f"{b:02X}" for b in value[:preview_bytes])
        ellipsis = " ..." if len(value) > preview_bytes else ""
        return f"<BLOB {len(value):,} bytes: {hex_preview}{ellipsis}>"

    def _format_plist_key(self, key: object) -> str:
        """Format a plist dictionary key."""
        if isinstance(key, str):
            if "\n" not in key and ":" not in key:
                return key
            return json.dumps(key, ensure_ascii=False)
        return self._format_plist_scalar(key)

    def _format_plist_scalar(self, value: object) -> str:
        """Format a scalar plist value."""
        if isinstance(value, str):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, bytes):
            return self._format_blob_preview(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, bool):
            return "true" if value else "false"
        if value is None:
            return "null"
        if isinstance(value, int | float):
            return str(value)
        return repr(value)

    def _format_plist_value(self, value: object, indent: int = 0) -> str:
        """Format a decoded plist value as readable key/value text."""
        prefix = " " * indent
        if isinstance(value, dict):
            if not value:
                return f"{prefix}{{}}"

            lines = []
            for key, item in value.items():
                formatted_key = self._format_plist_key(key)
                if isinstance(item, dict | list):
                    lines.append(f"{prefix}{formatted_key}:")
                    lines.append(self._format_plist_value(item, indent + 2))
                else:
                    lines.append(f"{prefix}{formatted_key}: {self._format_plist_scalar(item)}")
            return "\n".join(lines)

        if isinstance(value, list):
            if not value:
                return f"{prefix}[]"

            lines = []
            for item in value:
                if isinstance(item, dict | list):
                    lines.append(f"{prefix}-")
                    lines.append(self._format_plist_value(item, indent + 2))
                else:
                    lines.append(f"{prefix}- {self._format_plist_scalar(item)}")
            return "\n".join(lines)

        return f"{prefix}{self._format_plist_scalar(value)}"

    def _format_hex_dump(self, data: bytes) -> str:
        """Format binary data as a hex dump."""
        hex_lines = []
        for i in range(0, len(data), 16):
            chunk = data[i : i + 16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            hex_lines.append(f"{i:08X}  {hex_part:<48}  {ascii_part}")
        return f"BLOB ({len(data):,} bytes)\n\n" + "\n".join(hex_lines)

    def _format_decoded_plist(self) -> tuple[bool, str]:
        """Decode and format the raw binary plist value."""
        if not isinstance(self.raw_value, bytes):
            return False, "N/A (not binary data)"

        try:
            plist_value = plistlib.loads(self.raw_value)
        except (plistlib.InvalidFileException, ValueError, TypeError, OverflowError) as error:
            return False, f"Unable to decode binary plist: {error}"

        return True, self._format_plist_value(plist_value)

    def _format_blob_value(self) -> str:
        """Format a blob as either a hex dump or decoded binary plist."""
        if not isinstance(self.raw_value, bytes):
            return "N/A (not binary data)"

        hex_dump = self._format_hex_dump(self.raw_value)
        if not self._show_decoded_plist or not self._is_binary_plist():
            return hex_dump

        decoded, decoded_plist = self._format_decoded_plist()
        if decoded:
            return f"Decoded binary plist\n\n{decoded_plist}"

        return f"{decoded_plist}\n\n{hex_dump}"

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
        if isinstance(self.raw_value, bytes):
            raw_value = self._format_blob_value()
        else:
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

    def _hint_text(self) -> str:
        """Return the footer hint text."""
        if self._is_binary_plist():
            action = "hide" if self._show_decoded_plist else "show"
            return f"Press P to {action} decoded plist | Press Escape to close"
        return "Press Escape to close"

    def compose(self) -> ComposeResult:
        display_value = self._build_display_value()
        with Vertical():
            yield Label(f"Column: {self.column_name}")
            yield TextArea(display_value, read_only=True, id="cell-content")
            yield Label(self._hint_text(), classes="hint", id="cell-viewer-hint")

    def action_toggle_plist(self) -> None:
        """Toggle the decoded plist view for binary plist blobs."""
        if not self._is_binary_plist():
            return

        self._show_decoded_plist = not self._show_decoded_plist
        self.query_one("#cell-content", TextArea).load_text(self._build_display_value())
        self.query_one("#cell-viewer-hint", Label).update(self._hint_text())

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)
