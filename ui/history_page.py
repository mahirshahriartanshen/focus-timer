"""
History page widget for the Focus Timer application.
Displays session history with filtering and export capabilities.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QTableWidget, QTableWidgetItem,
    QGroupBox, QMessageBox, QFileDialog, QHeaderView, QFrame
)
from PySide6.QtCore import Qt, QDate, Slot
from PySide6.QtGui import QFont, QColor

from core.models import Session, Group
from core.storage import Storage


class HistoryPage(QWidget):
    """
    History page showing session records with filtering and statistics.
    """

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

        # Statistics section
        stats_box = QGroupBox("Statistics")
        stats_layout = QHBoxLayout(stats_box)
        stats_layout.setSpacing(40)

        # Today's total
        today_layout = QVBoxLayout()
        today_label = QLabel("Today")
        today_label.setStyleSheet("color: #a0a0a0; font-size: 13px;")
        today_layout.addWidget(today_label)
        self.today_total_label = QLabel("0h 0m")
        today_font = QFont()
        today_font.setPointSize(20)
        today_font.setBold(True)
        self.today_total_label.setFont(today_font)
        self.today_total_label.setStyleSheet("color: #66BB6A; font-size: 24px;")
        today_layout.addWidget(self.today_total_label)
        stats_layout.addLayout(today_layout)

        # This week's total
        week_layout = QVBoxLayout()
        week_label = QLabel("This Week")
        week_label.setStyleSheet("color: #a0a0a0; font-size: 13px;")
        week_layout.addWidget(week_label)
        self.week_total_label = QLabel("0h 0m")
        self.week_total_label.setFont(today_font)
        self.week_total_label.setStyleSheet("color: #42A5F5; font-size: 24px;")
        week_layout.addWidget(self.week_total_label)
        stats_layout.addLayout(week_layout)

        # Total sessions
        sessions_layout = QVBoxLayout()
        sessions_label = QLabel("Sessions Today")
        sessions_label.setStyleSheet("color: #a0a0a0; font-size: 13px;")
        sessions_layout.addWidget(sessions_label)
        self.sessions_count_label = QLabel("0")
        self.sessions_count_label.setFont(today_font)
        self.sessions_count_label.setStyleSheet("color: #FFA726; font-size: 24px;")
        sessions_layout.addWidget(self.sessions_count_label)
        stats_layout.addLayout(sessions_layout)

        stats_layout.addStretch()
        layout.addWidget(stats_box)

        # Group totals table
        group_box = QGroupBox("Focus Time by Category")
        group_layout = QVBoxLayout(group_box)
        
        self.group_table = QTableWidget()
        self.group_table.setColumnCount(3)
        self.group_table.setHorizontalHeaderLabels(["Category", "Total Time", "Sessions"])
        self.group_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.group_table.setMaximumHeight(150)
        self.group_table.setAlternatingRowColors(True)
        self.group_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.group_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        group_layout.addWidget(self.group_table)
        
        layout.addWidget(group_box)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Filter section
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Category:"))
        self.filter_group_combo = QComboBox()
        self.filter_group_combo.setMinimumWidth(150)
        filter_layout.addWidget(self.filter_group_combo)

        filter_layout.addWidget(QLabel("From:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        filter_layout.addWidget(self.start_date)

        filter_layout.addWidget(QLabel("To:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        filter_layout.addWidget(self.end_date)

        self.filter_btn = QPushButton("Filter")
        self.filter_btn.setMinimumWidth(80)
        filter_layout.addWidget(self.filter_btn)

        self.export_btn = QPushButton("Export CSV")
        self.export_btn.setMinimumWidth(100)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        filter_layout.addWidget(self.export_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Sessions table
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(7)
        self.sessions_table.setHorizontalHeaderLabels([
            "Date", "Category", "Start", "End", 
            "Planned", "Actual", "Status"
        ])
        self.sessions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sessions_table.setAlternatingRowColors(True)
        self.sessions_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.sessions_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.sessions_table)

    def _connect_signals(self):
        """Connect widget signals."""
        self.filter_btn.clicked.connect(self._apply_filter)
        self.export_btn.clicked.connect(self._export_csv)

    def refresh(self):
        """Refresh all data on the page."""
        self._load_groups()
        self._update_statistics()
        self._update_group_totals()
        self._apply_filter()

    def _load_groups(self):
        """Load groups for filter combo."""
        self._groups = self.storage.get_all_groups()
        current_data = self.filter_group_combo.currentData()
        
        self.filter_group_combo.clear()
        self.filter_group_combo.addItem("All Categories", None)
        for group in self._groups:
            self.filter_group_combo.addItem(group.name, group.id)
        
        # Restore selection if possible
        if current_data is not None:
            for i in range(self.filter_group_combo.count()):
                if self.filter_group_combo.itemData(i) == current_data:
                    self.filter_group_combo.setCurrentIndex(i)
                    break

    def _update_statistics(self):
        """Update today/week statistics."""
        # Today's total
        today_seconds = self.storage.get_today_total_seconds()
        hours = today_seconds // 3600
        minutes = (today_seconds % 3600) // 60
        self.today_total_label.setText(f"{hours}h {minutes}m")

        # This week's total
        week_seconds = self.storage.get_week_total_seconds()
        hours = week_seconds // 3600
        minutes = (week_seconds % 3600) // 60
        self.week_total_label.setText(f"{hours}h {minutes}m")

        # Today's session count
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        sessions = self.storage.get_sessions(
            start_date=today,
            end_date=tomorrow,
            limit=1000
        )
        self.sessions_count_label.setText(str(len(sessions)))

    def _update_group_totals(self):
        """Update group totals table."""
        # Get totals for the current filter period
        start_date = datetime(
            self.start_date.date().year(),
            self.start_date.date().month(),
            self.start_date.date().day()
        )
        end_date = datetime(
            self.end_date.date().year(),
            self.end_date.date().month(),
            self.end_date.date().day(),
            23, 59, 59
        )

        totals = self.storage.get_group_totals(start_date, end_date)

        self.group_table.setRowCount(len(totals))
        for row, (group, total_seconds, session_count) in enumerate(totals):
            # Category name with color indicator
            name_item = QTableWidgetItem(group.name)
            name_item.setForeground(QColor(group.color))
            self.group_table.setItem(row, 0, name_item)

            # Total time
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            time_item = QTableWidgetItem(f"{hours}h {minutes}m")
            self.group_table.setItem(row, 1, time_item)

            # Session count
            count_item = QTableWidgetItem(str(session_count))
            self.group_table.setItem(row, 2, count_item)

    @Slot()
    def _apply_filter(self):
        """Apply date and group filters to sessions table."""
        # Parse dates
        start_date = datetime(
            self.start_date.date().year(),
            self.start_date.date().month(),
            self.start_date.date().day()
        )
        end_date = datetime(
            self.end_date.date().year(),
            self.end_date.date().month(),
            self.end_date.date().day(),
            23, 59, 59
        )

        # Get group filter
        group_id = self.filter_group_combo.currentData()

        # Fetch sessions
        sessions = self.storage.get_sessions(
            group_id=group_id,
            start_date=start_date,
            end_date=end_date,
            limit=500
        )

        # Build group name lookup
        group_names = {g.id: g.name for g in self._groups}

        # Populate table
        self.sessions_table.setRowCount(len(sessions))
        for row, session in enumerate(sessions):
            # Date
            dt = datetime.fromtimestamp(session.start_ts)
            date_item = QTableWidgetItem(dt.strftime("%Y-%m-%d"))
            self.sessions_table.setItem(row, 0, date_item)

            # Category
            group_name = group_names.get(session.group_id, "Unknown")
            group_item = QTableWidgetItem(group_name)
            self.sessions_table.setItem(row, 1, group_item)

            # Start time
            start_item = QTableWidgetItem(dt.strftime("%H:%M"))
            self.sessions_table.setItem(row, 2, start_item)

            # End time
            end_dt = datetime.fromtimestamp(session.end_ts)
            end_item = QTableWidgetItem(end_dt.strftime("%H:%M"))
            self.sessions_table.setItem(row, 3, end_item)

            # Planned duration
            planned_min = session.planned_seconds // 60
            planned_item = QTableWidgetItem(f"{planned_min} min")
            self.sessions_table.setItem(row, 4, planned_item)

            # Actual duration
            actual_min = session.actual_seconds // 60
            actual_item = QTableWidgetItem(f"{actual_min} min")
            self.sessions_table.setItem(row, 5, actual_item)

            # Status
            status_item = QTableWidgetItem(session.status.capitalize())
            if session.status == "completed":
                status_item.setForeground(QColor("#66BB6A"))
            else:
                status_item.setForeground(QColor("#EF5350"))
            self.sessions_table.setItem(row, 6, status_item)

        # Update group totals for the filter period
        self._update_group_totals()

    @Slot()
    def _export_csv(self):
        """Export filtered sessions to CSV file."""
        # Get current filter settings
        start_date = datetime(
            self.start_date.date().year(),
            self.start_date.date().month(),
            self.start_date.date().day()
        )
        end_date = datetime(
            self.end_date.date().year(),
            self.end_date.date().month(),
            self.end_date.date().day(),
            23, 59, 59
        )
        group_id = self.filter_group_combo.currentData()

        # Get save path
        default_name = f"focus_sessions_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Sessions to CSV",
            default_name,
            "CSV Files (*.csv)"
        )

        if not filepath:
            return

        try:
            count = self.storage.export_to_csv(
                filepath,
                start_date=start_date,
                end_date=end_date,
                group_id=group_id
            )
            QMessageBox.information(
                self,
                "Export Complete",
                f"Successfully exported {count} sessions to:\n{filepath}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export sessions:\n{str(e)}"
            )
