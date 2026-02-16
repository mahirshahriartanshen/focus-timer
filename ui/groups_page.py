"""
Groups page widget for the Focus Timer application.
Provides CRUD operations for managing focus categories/groups.
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QTableWidget, QTableWidgetItem,
    QGroupBox, QMessageBox, QDialog, QDialogButtonBox,
    QFormLayout, QHeaderView, QColorDialog
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor

from core.models import Group
from core.storage import Storage


class GroupEditDialog(QDialog):
    """Dialog for creating or editing a group."""

    def __init__(
        self,
        group: Optional[Group] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self.group = group or Group()
        self.is_edit = group is not None and group.id is not None
        
        self.setWindowTitle("Edit Category" if self.is_edit else "New Category")
        self.setMinimumWidth(350)
        
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Form layout
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Study, Work, Coding")
        form_layout.addRow("Name:", self.name_edit)

        self.focus_spin = QSpinBox()
        self.focus_spin.setRange(1, 180)
        self.focus_spin.setValue(25)
        self.focus_spin.setSuffix(" minutes")
        form_layout.addRow("Default Focus:", self.focus_spin)

        self.break_spin = QSpinBox()
        self.break_spin.setRange(1, 60)
        self.break_spin.setValue(5)
        self.break_spin.setSuffix(" minutes")
        form_layout.addRow("Default Break:", self.break_spin)

        # Color picker
        color_layout = QHBoxLayout()
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(30, 30)
        self.color_preview.setStyleSheet(
            f"background-color: {self.group.color}; border: 1px solid #ccc; border-radius: 3px;"
        )
        color_layout.addWidget(self.color_preview)
        
        self.color_btn = QPushButton("Choose Color")
        self.color_btn.clicked.connect(self._choose_color)
        color_layout.addWidget(self.color_btn)
        color_layout.addStretch()
        
        form_layout.addRow("Color:", color_layout)

        layout.addLayout(form_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_data(self):
        """Load group data into form fields."""
        self.name_edit.setText(self.group.name)
        self.focus_spin.setValue(self.group.default_focus_minutes)
        self.break_spin.setValue(self.group.default_break_minutes)
        self._update_color_preview()

    def _update_color_preview(self):
        """Update the color preview label."""
        self.color_preview.setStyleSheet(
            f"background-color: {self.group.color}; border: 1px solid #505050; border-radius: 3px;"
        )

    @Slot()
    def _choose_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(
            QColor(self.group.color),
            self,
            "Choose Category Color"
        )
        if color.isValid():
            self.group.color = color.name()
            self._update_color_preview()

    @Slot()
    def _on_accept(self):
        """Validate and accept the dialog."""
        name = self.name_edit.text().strip()
        
        if not name:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please enter a category name."
            )
            return
        
        self.group.name = name
        self.group.default_focus_minutes = self.focus_spin.value()
        self.group.default_break_minutes = self.break_spin.value()
        
        self.accept()

    def get_group(self) -> Group:
        """Return the edited group."""
        return self.group


class GroupsPage(QWidget):
    """
    Groups management page with CRUD operations.
    """

    # Signal emitted when groups are modified
    groups_changed = Signal()

    def __init__(self, storage: Storage, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.storage = storage
        self._groups: List[Group] = []
        
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("Manage Categories")
        header_font = header.font()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        description = QLabel(
            "Create categories to organize your focus sessions. "
            "Each category can have its own default focus and break durations."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #a0a0a0;")
        layout.addWidget(description)

        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("+ Add Category")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        toolbar_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setEnabled(False)
        toolbar_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #404040;
                color: #606060;
            }
        """)
        toolbar_layout.addWidget(self.delete_btn)

        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)

        # Groups table
        self.groups_table = QTableWidget()
        self.groups_table.setColumnCount(5)
        self.groups_table.setHorizontalHeaderLabels([
            "Color", "Name", "Default Focus", "Default Break", "Created"
        ])
        self.groups_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.groups_table.setColumnWidth(0, 60)
        self.groups_table.setColumnWidth(2, 120)
        self.groups_table.setColumnWidth(3, 120)
        self.groups_table.setColumnWidth(4, 120)
        self.groups_table.setAlternatingRowColors(True)
        self.groups_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.groups_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.groups_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.groups_table)

    def _connect_signals(self):
        """Connect widget signals."""
        self.add_btn.clicked.connect(self._on_add)
        self.edit_btn.clicked.connect(self._on_edit)
        self.delete_btn.clicked.connect(self._on_delete)
        self.groups_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.groups_table.doubleClicked.connect(self._on_edit)

    def refresh(self):
        """Refresh the groups list."""
        self._groups = self.storage.get_all_groups()
        self._populate_table()

    def _populate_table(self):
        """Populate the table with groups data."""
        self.groups_table.setRowCount(len(self._groups))
        
        for row, group in enumerate(self._groups):
            # Color indicator
            color_item = QTableWidgetItem()
            color_item.setBackground(QColor(group.color))
            color_item.setData(Qt.ItemDataRole.UserRole, group.id)
            self.groups_table.setItem(row, 0, color_item)

            # Name
            name_item = QTableWidgetItem(group.name)
            self.groups_table.setItem(row, 1, name_item)

            # Default focus
            focus_item = QTableWidgetItem(f"{group.default_focus_minutes} min")
            focus_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.groups_table.setItem(row, 2, focus_item)

            # Default break
            break_item = QTableWidgetItem(f"{group.default_break_minutes} min")
            break_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.groups_table.setItem(row, 3, break_item)

            # Created date
            from datetime import datetime
            created = datetime.fromtimestamp(group.created_at)
            created_item = QTableWidgetItem(created.strftime("%Y-%m-%d"))
            created_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.groups_table.setItem(row, 4, created_item)

    def _get_selected_group(self) -> Optional[Group]:
        """Get the currently selected group."""
        selected = self.groups_table.selectedItems()
        if not selected:
            return None
        
        row = selected[0].row()
        group_id = self.groups_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        for group in self._groups:
            if group.id == group_id:
                return group
        return None

    @Slot()
    def _on_selection_changed(self):
        """Handle table selection change."""
        has_selection = len(self.groups_table.selectedItems()) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)

    @Slot()
    def _on_add(self):
        """Handle add button click."""
        dialog = GroupEditDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            group = dialog.get_group()
            try:
                self.storage.create_group(group)
                self.refresh()
                self.groups_changed.emit()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create category:\n{str(e)}"
                )

    @Slot()
    def _on_edit(self):
        """Handle edit button click or double-click."""
        group = self._get_selected_group()
        if not group:
            return
        
        # Create a copy for editing
        edit_group = Group(
            id=group.id,
            name=group.name,
            default_focus_minutes=group.default_focus_minutes,
            default_break_minutes=group.default_break_minutes,
            color=group.color,
            created_at=group.created_at
        )
        
        dialog = GroupEditDialog(edit_group, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_group = dialog.get_group()
            try:
                self.storage.update_group(updated_group)
                self.refresh()
                self.groups_changed.emit()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to update category:\n{str(e)}"
                )

    @Slot()
    def _on_delete(self):
        """Handle delete button click."""
        group = self._get_selected_group()
        if not group:
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{group.name}'?\n\n"
            "This will also delete all sessions associated with this category.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.storage.delete_group(group.id)
                self.refresh()
                self.groups_changed.emit()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete category:\n{str(e)}"
                )
