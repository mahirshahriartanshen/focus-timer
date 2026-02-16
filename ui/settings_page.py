"""
Settings page widget for the Focus Timer application.
Allows users to configure application behavior.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QGroupBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont

from core.models import AppSettings
from core.storage import Storage
from core.keep_awake import get_keep_awake_manager
from core.notifications import get_notification_manager


class SettingsPage(QWidget):
    """
    Settings page for configuring application behavior.
    """

    # Signal emitted when settings change
    settings_changed = Signal(AppSettings)

    def __init__(self, storage: Storage, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.storage = storage
        self._settings = AppSettings()
        
        self._setup_ui()
        self._connect_signals()
        self._load_settings()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header = QLabel("Settings")
        header_font = QFont()
        header_font.setPointSize(18)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        # Timer Behavior section
        timer_box = QGroupBox("Timer Behavior")
        timer_layout = QVBoxLayout(timer_box)
        timer_layout.setSpacing(12)

        self.auto_break_check = QCheckBox("Auto-start break after focus session")
        self.auto_break_check.setToolTip(
            "Automatically start the break timer when focus session completes"
        )
        timer_layout.addWidget(self.auto_break_check)

        self.auto_focus_check = QCheckBox("Auto-start focus after break")
        self.auto_focus_check.setToolTip(
            "Automatically start a new focus session when break completes"
        )
        timer_layout.addWidget(self.auto_focus_check)

        layout.addWidget(timer_box)

        # Notifications section
        notif_box = QGroupBox("Notifications")
        notif_layout = QVBoxLayout(notif_box)
        notif_layout.setSpacing(12)

        self.sound_check = QCheckBox("Play sound on phase change")
        self.sound_check.setToolTip(
            "Play a notification sound when transitioning between focus and break"
        )
        notif_layout.addWidget(self.sound_check)

        self.notification_check = QCheckBox("Show desktop notifications")
        self.notification_check.setToolTip(
            "Show system notifications when timer phases change"
        )
        notif_layout.addWidget(self.notification_check)

        layout.addWidget(notif_box)

        # System section
        system_box = QGroupBox("System")
        system_layout = QVBoxLayout(system_box)
        system_layout.setSpacing(12)

        self.keep_awake_check = QCheckBox("Prevent screen sleep during focus")
        self.keep_awake_check.setToolTip(
            "Keep the screen awake while a focus session is running"
        )
        system_layout.addWidget(self.keep_awake_check)

        self.log_breaks_check = QCheckBox("Log break sessions to history")
        self.log_breaks_check.setToolTip(
            "Include break sessions in the session history (not just focus sessions)"
        )
        system_layout.addWidget(self.log_breaks_check)

        layout.addWidget(system_box)

        # Data Management section
        data_box = QGroupBox("Data Management")
        data_layout = QVBoxLayout(data_box)
        data_layout.setSpacing(12)

        data_info = QLabel(
            "Session data is stored locally in your application data folder."
        )
        data_info.setStyleSheet("color: #a0a0a0;")
        data_info.setWordWrap(True)
        data_layout.addWidget(data_info)

        # Show data location
        from core.storage import get_app_data_dir
        data_path = get_app_data_dir()
        path_label = QLabel(f"Location: {data_path}")
        path_label.setStyleSheet("color: #808080; font-size: 11px;")
        path_label.setWordWrap(True)
        path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        data_layout.addWidget(path_label)

        layout.addWidget(data_box)

        # About section
        about_box = QGroupBox("About")
        about_layout = QVBoxLayout(about_box)

        about_text = QLabel(
            "<b>Focus Timer</b> v1.0<br>"
            "A local-only Pomodoro-style focus timer.<br><br>"
            "Built with PySide6 (Qt) and SQLite.<br>"
            "No cloud, no tracking, just productivity."
        )
        about_text.setWordWrap(True)
        about_layout.addWidget(about_text)

        layout.addWidget(about_box)

        # Spacer
        layout.addStretch()

    def _connect_signals(self):
        """Connect widget signals."""
        self.auto_break_check.toggled.connect(self._on_setting_changed)
        self.auto_focus_check.toggled.connect(self._on_setting_changed)
        self.sound_check.toggled.connect(self._on_setting_changed)
        self.notification_check.toggled.connect(self._on_setting_changed)
        self.keep_awake_check.toggled.connect(self._on_setting_changed)
        self.log_breaks_check.toggled.connect(self._on_setting_changed)

    def _load_settings(self):
        """Load settings from storage."""
        self._settings = self.storage.get_settings()
        
        # Block signals while loading to prevent save loops
        for checkbox in [
            self.auto_break_check, self.auto_focus_check,
            self.sound_check, self.notification_check,
            self.keep_awake_check, self.log_breaks_check
        ]:
            checkbox.blockSignals(True)
        
        self.auto_break_check.setChecked(self._settings.auto_start_break)
        self.auto_focus_check.setChecked(self._settings.auto_start_focus)
        self.sound_check.setChecked(self._settings.sound_enabled)
        self.notification_check.setChecked(self._settings.notification_enabled)
        self.keep_awake_check.setChecked(self._settings.keep_screen_awake)
        self.log_breaks_check.setChecked(self._settings.log_breaks)
        
        # Unblock signals
        for checkbox in [
            self.auto_break_check, self.auto_focus_check,
            self.sound_check, self.notification_check,
            self.keep_awake_check, self.log_breaks_check
        ]:
            checkbox.blockSignals(False)
        
        # Apply settings to managers
        self._apply_settings()

    def _apply_settings(self):
        """Apply settings to the relevant managers."""
        # Keep awake manager
        keep_awake = get_keep_awake_manager()
        keep_awake.enabled = self._settings.keep_screen_awake
        
        # Notification manager
        notif_manager = get_notification_manager()
        notif_manager.sound_enabled = self._settings.sound_enabled
        notif_manager.notification_enabled = self._settings.notification_enabled

    @Slot()
    def _on_setting_changed(self):
        """Handle settings change."""
        self._settings.auto_start_break = self.auto_break_check.isChecked()
        self._settings.auto_start_focus = self.auto_focus_check.isChecked()
        self._settings.sound_enabled = self.sound_check.isChecked()
        self._settings.notification_enabled = self.notification_check.isChecked()
        self._settings.keep_screen_awake = self.keep_awake_check.isChecked()
        self._settings.log_breaks = self.log_breaks_check.isChecked()
        
        # Save to storage
        self.storage.save_settings(self._settings)
        
        # Apply settings
        self._apply_settings()
        
        # Emit signal
        self.settings_changed.emit(self._settings)

    def get_settings(self) -> AppSettings:
        """Get current settings."""
        return self._settings
