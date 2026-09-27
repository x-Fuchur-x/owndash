from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QGridLayout, QLabel, QWidget


# Shared visual contract for read-only information views. Keeping the label
# column identical makes all current values begin on one calm vertical line.
INFO_LABEL_COLUMN_WIDTH = 190
INFO_HORIZONTAL_SPACING = 22
INFO_VERTICAL_SPACING = 9


def make_info_label(
    text: str,
    parent: QWidget | None = None,
    *,
    label_width: int = INFO_LABEL_COLUMN_WIDTH,
) -> QLabel:
    label = QLabel(text, parent)
    label.setFixedWidth(label_width)
    label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
    label.setWordWrap(True)
    return label


def configure_info_form(
    form: QFormLayout,
    *,
    label_width: int = INFO_LABEL_COLUMN_WIDTH,
) -> QFormLayout:
    """Apply the OwnDash read-only key/value column contract to a form."""
    form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    form.setRowWrapPolicy(QFormLayout.DontWrapRows)
    form.setLabelAlignment(Qt.AlignLeft | Qt.AlignTop)
    form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
    form.setHorizontalSpacing(INFO_HORIZONTAL_SPACING)
    form.setVerticalSpacing(INFO_VERTICAL_SPACING)

    # QFormLayout may create QLabel instances itself for string labels. Apply
    # the same width to those labels too, including forms configured after rows
    # were populated.
    for row in range(form.rowCount()):
        item = form.itemAt(row, QFormLayout.LabelRole)
        widget = item.widget() if item is not None else None
        if isinstance(widget, QLabel):
            widget.setFixedWidth(label_width)
            widget.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            widget.setWordWrap(True)
    return form


def add_info_form_row(
    form: QFormLayout,
    title: str,
    field: QWidget,
    *,
    parent: QWidget | None = None,
    label_width: int = INFO_LABEL_COLUMN_WIDTH,
) -> QLabel:
    """Add one key/value row with an explicit fixed-width key label."""
    label = make_info_label(title, parent, label_width=label_width)
    form.addRow(label, field)
    return label


def configure_info_grid(
    grid: QGridLayout,
    *,
    label_column: int = 0,
    value_column: int = 1,
    label_width: int = INFO_LABEL_COLUMN_WIDTH,
) -> QGridLayout:
    """Apply the same key/value geometry to grid-based information cards."""
    grid.setHorizontalSpacing(INFO_HORIZONTAL_SPACING)
    grid.setVerticalSpacing(INFO_VERTICAL_SPACING)
    grid.setColumnMinimumWidth(label_column, label_width)
    grid.setColumnStretch(label_column, 0)
    grid.setColumnStretch(value_column, 1)
    return grid
