#!/usr/bin/env python3
"""
Focus Timer - A local-only Pomodoro-style focus timer application.

A simple, clean, and effective focus timer with:
- Customizable focus and break durations
- Category-based session organization
- Local session history with statistics
- Desktop notifications and sound alerts
- Screen sleep prevention during focus sessions

Usage:
    pip install PySide6
    python main.py

Author: Focus Timer
License: MIT
"""

import sys
import signal
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt


def setup_exception_handling():
    """Set up exception handling for cleaner error display."""
    def exception_hook(exctype, value, traceback):
        print(f"Unhandled exception: {exctype.__name__}: {value}")
        sys.__excepthook__(exctype, value, traceback)
    
    sys.excepthook = exception_hook


def setup_signal_handlers(app: QApplication):
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        print("\nReceived interrupt signal, shutting down...")
        app.quit()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point for the Focus Timer application."""
    # Set up exception handling
    setup_exception_handling()
    
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Focus Timer")
    app.setApplicationDisplayName("Focus Timer")
    app.setOrganizationName("FocusTimer")
    app.setOrganizationDomain("focustimer.local")
    
    # Set application style
    app.setStyle("Fusion")
    
    # Apply dark theme stylesheet
    app.setStyleSheet("""
        /* ==================== DARK THEME ==================== */
        
        /* Main Window & Widgets */
        QMainWindow, QWidget {
            background-color: #1e1e1e;
            color: #e0e0e0;
        }
        
        /* Tab Widget */
        QTabWidget::pane {
            border: none;
            background-color: #252525;
        }
        QTabBar::tab {
            background-color: #2d2d2d;
            color: #b0b0b0;
            padding: 12px 25px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            font-size: 13px;
        }
        QTabBar::tab:selected {
            background-color: #252525;
            color: #ffffff;
            font-weight: bold;
        }
        QTabBar::tab:hover:!selected {
            background-color: #383838;
            color: #ffffff;
        }
        
        /* Group Box */
        QGroupBox {
            font-weight: bold;
            font-size: 13px;
            color: #e0e0e0;
            border: 1px solid #404040;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 12px;
            background-color: #2a2a2a;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
            color: #4CAF50;
        }
        
        /* Labels */
        QLabel {
            color: #e0e0e0;
            font-size: 13px;
        }
        
        /* ComboBox */
        QComboBox {
            padding: 8px 12px;
            border: 1px solid #404040;
            border-radius: 5px;
            background-color: #2d2d2d;
            color: #ffffff;
            font-size: 13px;
            min-height: 20px;
        }
        QComboBox:hover {
            border-color: #4CAF50;
            background-color: #353535;
        }
        QComboBox:focus {
            border-color: #4CAF50;
        }
        QComboBox::drop-down {
            border: none;
            width: 30px;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid #4CAF50;
            margin-right: 10px;
        }
        QComboBox QAbstractItemView {
            background-color: #2d2d2d;
            color: #ffffff;
            selection-background-color: #4CAF50;
            selection-color: #ffffff;
            border: 1px solid #404040;
            padding: 5px;
        }
        
        /* SpinBox */
        QSpinBox {
            padding: 8px;
            border: 1px solid #404040;
            border-radius: 5px;
            background-color: #2d2d2d;
            color: #ffffff;
            font-size: 13px;
        }
        QSpinBox:hover {
            border-color: #4CAF50;
        }
        QSpinBox:focus {
            border-color: #4CAF50;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            background-color: #404040;
            border: none;
            width: 20px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #4CAF50;
        }
        
        /* CheckBox */
        QCheckBox {
            spacing: 10px;
            color: #e0e0e0;
            font-size: 13px;
        }
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 2px solid #404040;
            background-color: #2d2d2d;
        }
        QCheckBox::indicator:hover {
            border-color: #4CAF50;
        }
        QCheckBox::indicator:checked {
            background-color: #4CAF50;
            border-color: #4CAF50;
        }
        
        /* Table Widget */
        QTableWidget {
            border: 1px solid #404040;
            border-radius: 5px;
            gridline-color: #353535;
            background-color: #252525;
            color: #e0e0e0;
            font-size: 12px;
        }
        QTableWidget::item {
            padding: 8px;
            color: #e0e0e0;
        }
        QTableWidget::item:selected {
            background-color: #4CAF50;
            color: #ffffff;
        }
        QTableWidget::item:hover {
            background-color: #353535;
        }
        QHeaderView::section {
            background-color: #2d2d2d;
            color: #ffffff;
            padding: 10px;
            border: none;
            border-bottom: 2px solid #4CAF50;
            font-weight: bold;
            font-size: 12px;
        }
        
        /* Date Edit */
        QDateEdit {
            padding: 8px;
            border: 1px solid #404040;
            border-radius: 5px;
            background-color: #2d2d2d;
            color: #ffffff;
            font-size: 13px;
        }
        QDateEdit:hover {
            border-color: #4CAF50;
        }
        QDateEdit::drop-down {
            border: none;
            width: 25px;
        }
        QCalendarWidget {
            background-color: #2d2d2d;
            color: #ffffff;
        }
        QCalendarWidget QToolButton {
            color: #ffffff;
            background-color: #2d2d2d;
            border: none;
            padding: 5px;
        }
        QCalendarWidget QToolButton:hover {
            background-color: #4CAF50;
        }
        
        /* Push Button - Default */
        QPushButton {
            padding: 10px 18px;
            border-radius: 5px;
            background-color: #404040;
            color: #ffffff;
            font-size: 13px;
            font-weight: bold;
            border: none;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QPushButton:pressed {
            background-color: #353535;
        }
        QPushButton:disabled {
            background-color: #2d2d2d;
            color: #606060;
        }
        
        /* Line Edit */
        QLineEdit {
            padding: 10px;
            border: 1px solid #404040;
            border-radius: 5px;
            background-color: #2d2d2d;
            color: #ffffff;
            font-size: 13px;
        }
        QLineEdit:hover {
            border-color: #505050;
        }
        QLineEdit:focus {
            border-color: #4CAF50;
        }
        QLineEdit::placeholder {
            color: #707070;
        }
        
        /* Scroll Bar */
        QScrollBar:vertical {
            background-color: #252525;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background-color: #404040;
            border-radius: 6px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #4CAF50;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QScrollBar:horizontal {
            background-color: #252525;
            height: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:horizontal {
            background-color: #404040;
            border-radius: 6px;
            min-width: 30px;
        }
        QScrollBar::handle:horizontal:hover {
            background-color: #4CAF50;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        
        /* Frame / Separator */
        QFrame[frameShape="4"] {
            color: #404040;
        }
        
        /* Dialog */
        QDialog {
            background-color: #1e1e1e;
            color: #e0e0e0;
        }
        
        /* Message Box */
        QMessageBox {
            background-color: #1e1e1e;
            color: #e0e0e0;
        }
        QMessageBox QLabel {
            color: #e0e0e0;
        }
        
        /* Tool Tip */
        QToolTip {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #4CAF50;
            padding: 5px;
            border-radius: 3px;
        }
        
        /* Menu */
        QMenu {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #404040;
            padding: 5px;
        }
        QMenu::item {
            padding: 8px 25px;
            border-radius: 3px;
        }
        QMenu::item:selected {
            background-color: #4CAF50;
            color: #ffffff;
        }
        
        /* Color Dialog */
        QColorDialog {
            background-color: #1e1e1e;
        }
    """)
    
    # Set up signal handlers
    setup_signal_handlers(app)
    
    # Import and create main window
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    
    # Run the application
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
