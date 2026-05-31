"""Tests for the cell viewer modal."""

from sqv.widgets.cell_viewer import CellViewerScreen


def test_numeric_interpretations() -> None:
    """Numeric values are shown with commas and date/time interpretations."""
    viewer = CellViewerScreen("amount", 1234567.8)

    assert viewer._format_value_with_commas() == "1,234,567.8"
    assert viewer._format_datetime_from_epoch(viewer.UNIX_EPOCH) == (
        "1970-01-15T06:56:07.800000Z"
    )
    assert viewer._format_datetime_from_epoch(viewer.MACOS_EPOCH) == (
        "2001-01-15T06:56:07.800000Z"
    )


def test_numeric_strings_do_not_show_interpretations() -> None:
    """Numeric strings are not treated as clear int or float values."""
    viewer = CellViewerScreen("amount", "1234567.80")

    display_value = viewer._build_display_value()

    assert display_value == "Raw value:\n1234567.8"


def test_non_numeric_values_do_not_show_interpretations() -> None:
    """Non-numeric values only show the raw display."""
    viewer = CellViewerScreen("name", "Alice")

    display_value = viewer._build_display_value()

    assert display_value == "Raw value:\nAlice"


def test_bool_values_do_not_show_interpretations() -> None:
    """Bool values are not treated as ints for derived display formats."""
    viewer = CellViewerScreen("enabled", True)

    display_value = viewer._build_display_value()

    assert display_value == "Raw value:\nTrue"


def test_build_display_value_preserves_raw_rendering() -> None:
    """The display still includes the raw value section before derived views."""
    viewer = CellViewerScreen("payload", '{"x": 1}')

    display_value = viewer._build_display_value()

    assert display_value.startswith('Raw value:\n{\n  "x": 1\n}')
    assert "Raw value with commas" not in display_value
    assert "Unix date/time" not in display_value
    assert "macOS date/time" not in display_value
