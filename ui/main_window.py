"""
Main window for the Focus Timer application.
Contains the tab widget with all pages.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QSystemTrayIcon, QMenu, QApplication, QMessageBox
)
from PySide6.QtCore import Qt, Slot, QSize
from PySide6.QtGui import QIcon, QAction, QCloseEvent, QPixmap, QPainter, QColor

from core.models import TimerState, TimerContext, Session
from core.storage import Storage
from core.timer_engine import TimerEngine
from core.keep_awake import get_keep_awake_manager
from core.notifications import get_notification_manager

from .timer_page import TimerPage
from .history_page import HistoryPage
from .groups_page import GroupsPage
from .settings_page import SettingsPage


def create_app_icon() -> QIcon:
    """Create a simple app icon programmatically."""
    sizes = [16, 32, 48, 64]
    icon = QIcon()
    
    for size in sizes:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw a timer circle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#4CAF50"))
        margin = size // 8
        painter.drawEllipse(margin, margin, size - 2*margin, size - 2*margin)
        
        # Draw inner circle (white)
        inner_margin = size // 4
        painter.setBrush(QColor("white"))
        painter.drawEllipse(
            inner_margin, inner_margin,
            size - 2*inner_margin, size - 2*inner_margin
        )
        
        # Draw timer hand
        painter.setBrush(QColor("#4CAF50"))
        center = size // 2
        hand_width = max(1, size // 10)
        painter.drawRect(
            center - hand_width // 2,
            inner_margin + size // 10,
            hand_width,
            center - inner_margin - size // 10
        )
        
        painter.end()
        icon.addPixmap(pixmap)
    
    return icon


class MainWindow(QMainWindow):
    """
    Main application window with tabbed interface.
    """

    def __init__(self):
        super().__init__()
        
        # Initialize storage and engine
        self.storage = Storage()
        self.timer_engine = TimerEngine(self.storage)
        
        # Set up UI
        self.setWindowTitle("Focus Timer")
        self.setMinimumSize(700, 550)
        self.resize(800, 600)
        
        # Create app icon
        self.app_icon = create_app_icon()
        self.setWindowIcon(self.app_icon)
        
        self._setup_ui()
        self._setup_tray()
        self._connect_signals()
        
        # Load initial data
        self._refresh_all()

    def _setup_ui(self):
        """Set up the main UI."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # Create pages
        self.timer_page = TimerPage(self.storage, self.timer_engine)
        self.history_page = HistoryPage(self.storage)
        self.groups_page = GroupsPage(self.storage)
        self.settings_page = SettingsPage(self.storage)
        
        # Add tabs
        self.tabs.addTab(self.timer_page, "Timer")
        self.tabs.addTab(self.history_page, "History")
        self.tabs.addTab(self.groups_page, "Categories")
        self.tabs.addTab(self.settings_page, "Settings")
        
        layout.addWidget(self.tabs)

    def _setup_tray(self):
        """Set up system tray icon."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        self.tray_icon.setToolTip("Focus Timer")
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self._show_window)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        self.tray_start_action = QAction("Start Focus", self)
        self.tray_start_action.triggered.connect(self._tray_start_focus)
        tray_menu.addAction(self.tray_start_action)
        
        self.tray_pause_action = QAction("Pause", self)
        self.tray_pause_action.triggered.connect(self._tray_toggle_pause)
        self.tray_pause_action.setEnabled(False)
        tray_menu.addAction(self.tray_pause_action)
        
        self.tray_stop_action = QAction("Stop", self)
        self.tray_stop_action.triggered.connect(self._tray_stop)
        self.tray_stop_action.setEnabled(False)
        tray_menu.addAction(self.tray_stop_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
        
        # Set tray icon for notifications
        notif_manager = get_notification_manager()
        notif_manager.set_tray_icon(self.tray_icon)

    def _connect_signals(self):
        """Connect signals from various components."""
        # Timer engine signals
        self.timer_engine.tick.connect(self._on_timer_tick)
        self.timer_engine.phase_changed.connect(self._on_phase_changed)
        self.timer_engine.session_completed.connect(self._on_session_completed)
        
        # Groups page signal
        self.groups_page.groups_changed.connect(self._on_groups_changed)
        
        # Tab changed
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _refresh_all(self):
        """Refresh all pages."""
        self.history_page.refresh()
        self.groups_page.refresh()

    @Slot(TimerContext)
    def _on_timer_tick(self, context: TimerContext):
        """Handle timer tick for tray updates."""
        if hasattr(self, 'tray_icon'):
            phase_name = {
                TimerState.IDLE: "Idle",
                TimerState.FOCUS: "Focus",
                TimerState.BREAK: "Break",
                TimerState.PAUSED: "Paused",
            }.get(context.state, "")
            
            if context.state != TimerState.IDLE:
                self.tray_icon.setToolTip(
                    f"Focus Timer - {phase_name}\n{context.format_remaining()}"
                )
            else:
                self.tray_icon.setToolTip("Focus Timer")

    @Slot(TimerState, TimerState)
    def _on_phase_changed(self, old_state: TimerState, new_state: TimerState):
        """Handle phase change for notifications and keep-awake."""
        keep_awake = get_keep_awake_manager()
        notif = get_notification_manager()
        
        # Handle keep-awake - keep screen on during FOCUS and BREAK
        if new_state == TimerState.FOCUS:
            keep_awake.start()
            if old_state == TimerState.IDLE:
                notif.notify_focus_start()
        elif new_state == TimerState.BREAK:
            # Keep screen awake during break too
            keep_awake.start()
            notif.notify_break_start()
        elif new_state == TimerState.IDLE:
            keep_awake.stop()
            if old_state == TimerState.FOCUS:
                notif.notify_focus_complete()
            elif old_state == TimerState.BREAK:
                notif.notify_break_complete()
        elif new_state == TimerState.PAUSED:
            # Keep awake even when paused (user might resume soon)
            pass  # Don't stop keep_awake when paused
        
        # Update tray menu
        if hasattr(self, 'tray_icon'):
            is_running = new_state in (TimerState.FOCUS, TimerState.BREAK)
            is_paused = new_state == TimerState.PAUSED
            
            self.tray_start_action.setEnabled(new_state == TimerState.IDLE)
            self.tray_pause_action.setEnabled(is_running or is_paused)
            self.tray_pause_action.setText("Resume" if is_paused else "Pause")
            self.tray_stop_action.setEnabled(is_running or is_paused)

    @Slot(Session)
    def _on_session_completed(self, session: Session):
        """Handle session completion."""
        # Refresh history if on that tab
        if self.tabs.currentWidget() == self.history_page:
            self.history_page.refresh()

    @Slot()
    def _on_groups_changed(self):
        """Handle groups modification."""
        # Refresh timer page groups
        self.timer_page.refresh_groups()

    @Slot(int)
    def _on_tab_changed(self, index: int):
        """Handle tab change."""
        widget = self.tabs.widget(index)
        if widget == self.history_page:
            self.history_page.refresh()

    @Slot(QSystemTrayIcon.ActivationReason)
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    @Slot()
    def _show_window(self):
        """Show and bring window to front."""
        self.show()
        self.raise_()
        self.activateWindow()

    @Slot()
    def _tray_start_focus(self):
        """Start focus from tray."""
        # Get current settings from timer page
        focus_min, break_min = self.timer_page._get_current_timing()
        group_id = self.timer_page.group_combo.currentData()
        self.timer_engine.start_focus(focus_min, break_min, group_id)

    @Slot()
    def _tray_toggle_pause(self):
        """Toggle pause from tray."""
        if self.timer_engine.is_paused:
            self.timer_engine.resume()
        else:
            self.timer_engine.pause()

    @Slot()
    def _tray_stop(self):
        """Stop timer from tray."""
        self.timer_engine.stop()

    @Slot()
    def _quit_app(self):
        """Quit the application."""
        self._cleanup()
        QApplication.quit()

    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        # Minimize to tray instead of closing if timer is running
        if self.timer_engine.is_running or self.timer_engine.is_paused:
            if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
                event.ignore()
                self.hide()
                self.tray_icon.showMessage(
                    "Focus Timer",
                    "Timer still running. Click tray icon to show window.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
                return
        
        # Otherwise, ask for confirmation if timer is running
        if self.timer_engine.is_running:
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "A timer is currently running. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        self._cleanup()
        event.accept()

    def _cleanup(self):
        """Clean up resources before exit."""
        # Stop timer and save session
        self.timer_engine.cleanup()
        
        # Stop keep-awake
        keep_awake = get_keep_awake_manager()
        keep_awake.cleanup()
        
        # Clean up notifications
        notif = get_notification_manager()
        notif.cleanup()
        
        # Hide tray icon
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
