"""
Timer page widget for the Focus Timer application.
Contains the main timer display, controls, and preset selection.
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QGroupBox, QCheckBox, QFrame,
    QSizePolicy
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont

from core.models import TimerState, TimerContext, Group, DEFAULT_PRESETS, AppSettings
from core.storage import Storage
from core.timer_engine import TimerEngine


class TimerPage(QWidget):
    """
    Main timer page with countdown display and controls.
    """

    def __init__(
        self,
        storage: Storage,
        timer_engine: TimerEngine,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self.storage = storage
        self.timer_engine = timer_engine
        
        # Current settings
        self._groups: List[Group] = []
        self._current_preset_index = 0
        self._use_custom = False
        
        self._setup_ui()
        self._connect_signals()
        self._load_groups()
        self._load_settings()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Phase label (FOCUS / BREAK / PAUSED / IDLE)
        self.phase_label = QLabel("IDLE")
        self.phase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        phase_font = QFont()
        phase_font.setPointSize(18)
        phase_font.setBold(True)
        self.phase_label.setFont(phase_font)
        self.phase_label.setStyleSheet("color: #808080; font-size: 20px;")
        layout.addWidget(self.phase_label)

        # Big countdown display
        self.time_label = QLabel("00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_font = QFont()
        time_font.setPointSize(72)
        time_font.setBold(True)
        self.time_label.setFont(time_font)
        self.time_label.setStyleSheet("color: #e0e0e0; font-size: 80px;")
        self.time_label.setMinimumHeight(120)
        layout.addWidget(self.time_label)

        # Progress info
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        layout.addWidget(self.progress_label)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Configuration section
        config_layout = QHBoxLayout()
        config_layout.setSpacing(20)

        # Group selection
        group_box = QGroupBox("Category")
        group_layout = QVBoxLayout(group_box)
        self.group_combo = QComboBox()
        self.group_combo.setMinimumWidth(150)
        group_layout.addWidget(self.group_combo)
        config_layout.addWidget(group_box)

        # Preset selection
        preset_box = QGroupBox("Preset")
        preset_layout = QVBoxLayout(preset_box)
        self.preset_combo = QComboBox()
        for preset in DEFAULT_PRESETS:
            self.preset_combo.addItem(str(preset))
        self.preset_combo.addItem("Custom")
        self.preset_combo.setMinimumWidth(180)
        preset_layout.addWidget(self.preset_combo)
        config_layout.addWidget(preset_box)

        # Custom duration inputs
        custom_box = QGroupBox("Custom Duration")
        custom_layout = QHBoxLayout(custom_box)
        
        custom_layout.addWidget(QLabel("Focus:"))
        self.focus_spin = QSpinBox()
        self.focus_spin.setRange(1, 180)
        self.focus_spin.setValue(25)
        self.focus_spin.setSuffix(" min")
        self.focus_spin.setEnabled(False)
        custom_layout.addWidget(self.focus_spin)
        
        custom_layout.addWidget(QLabel("Break:"))
        self.break_spin = QSpinBox()
        self.break_spin.setRange(1, 60)
        self.break_spin.setValue(5)
        self.break_spin.setSuffix(" min")
        self.break_spin.setEnabled(False)
        custom_layout.addWidget(self.break_spin)
        
        config_layout.addWidget(custom_box)
        
        layout.addLayout(config_layout)

        # Control buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        self.start_btn = QPushButton("Start Focus")
        self.start_btn.setMinimumSize(120, 45)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        button_layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setMinimumSize(100, 45)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e68a00;
            }
            QPushButton:disabled {
                background-color: #404040;
                color: #606060;
            }
        """)
        button_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setMinimumSize(100, 45)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #404040;
                color: #606060;
            }
        """)
        button_layout.addWidget(self.stop_btn)

        self.skip_break_btn = QPushButton("Skip Break")
        self.skip_break_btn.setMinimumSize(100, 45)
        self.skip_break_btn.setVisible(False)
        self.skip_break_btn.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        button_layout.addWidget(self.skip_break_btn)

        layout.addLayout(button_layout)

        # Options section
        options_layout = QHBoxLayout()
        options_layout.setSpacing(30)

        self.auto_break_check = QCheckBox("Auto-start break")
        self.auto_break_check.setChecked(True)
        options_layout.addWidget(self.auto_break_check)

        self.auto_focus_check = QCheckBox("Auto-start focus after break")
        self.auto_focus_check.setChecked(False)
        options_layout.addWidget(self.auto_focus_check)

        options_layout.addStretch()
        layout.addLayout(options_layout)

        # Spacer
        layout.addStretch()

    def _connect_signals(self):
        """Connect widget signals to slots."""
        # Timer engine signals
        self.timer_engine.tick.connect(self._on_tick)
        self.timer_engine.phase_changed.connect(self._on_phase_changed)

        # Button signals
        self.start_btn.clicked.connect(self._on_start_clicked)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.skip_break_btn.clicked.connect(self._on_skip_break_clicked)

        # Combo box signals
        self.group_combo.currentIndexChanged.connect(self._on_group_changed)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)

        # Option checkboxes
        self.auto_break_check.toggled.connect(self._on_options_changed)
        self.auto_focus_check.toggled.connect(self._on_options_changed)

    def _load_groups(self):
        """Load groups from storage."""
        self._groups = self.storage.get_all_groups()
        self.group_combo.clear()
        for group in self._groups:
            self.group_combo.addItem(group.name, group.id)

    def _load_settings(self):
        """Load settings from storage."""
        settings = self.storage.get_settings()
        self.auto_break_check.setChecked(settings.auto_start_break)
        self.auto_focus_check.setChecked(settings.auto_start_focus)

    def refresh_groups(self):
        """Refresh the groups list (called when groups are modified)."""
        current_id = self.group_combo.currentData()
        self._load_groups()
        
        # Try to reselect the previous group
        for i in range(self.group_combo.count()):
            if self.group_combo.itemData(i) == current_id:
                self.group_combo.setCurrentIndex(i)
                break

    def _get_current_timing(self) -> tuple:
        """Get current focus and break minutes based on selection."""
        if self._use_custom:
            return self.focus_spin.value(), self.break_spin.value()
        else:
            preset_index = self.preset_combo.currentIndex()
            if preset_index < len(DEFAULT_PRESETS):
                preset = DEFAULT_PRESETS[preset_index]
                return preset.focus_minutes, preset.break_minutes
            return self.focus_spin.value(), self.break_spin.value()

    @Slot()
    def _on_start_clicked(self):
        """Handle start button click."""
        focus_min, break_min = self._get_current_timing()
        group_id = self.group_combo.currentData()
        self.timer_engine.start_focus(focus_min, break_min, group_id)

    @Slot()
    def _on_pause_clicked(self):
        """Handle pause/resume button click."""
        if self.timer_engine.is_paused:
            self.timer_engine.resume()
        else:
            self.timer_engine.pause()

    @Slot()
    def _on_stop_clicked(self):
        """Handle stop button click."""
        self.timer_engine.stop()

    @Slot()
    def _on_skip_break_clicked(self):
        """Handle skip break button click."""
        self.timer_engine.skip_break()

    @Slot(int)
    def _on_group_changed(self, index: int):
        """Handle group selection change."""
        if index < 0 or index >= len(self._groups):
            return
        
        group = self._groups[index]
        
        # Update custom spinners with group defaults
        self.focus_spin.setValue(group.default_focus_minutes)
        self.break_spin.setValue(group.default_break_minutes)

    @Slot(int)
    def _on_preset_changed(self, index: int):
        """Handle preset selection change."""
        self._use_custom = (index == len(DEFAULT_PRESETS))
        self.focus_spin.setEnabled(self._use_custom)
        self.break_spin.setEnabled(self._use_custom)
        
        # Update spinners with preset values
        if not self._use_custom and index < len(DEFAULT_PRESETS):
            preset = DEFAULT_PRESETS[index]
            self.focus_spin.setValue(preset.focus_minutes)
            self.break_spin.setValue(preset.break_minutes)

    @Slot()
    def _on_options_changed(self):
        """Handle option checkbox changes."""
        settings = self.storage.get_settings()
        settings.auto_start_break = self.auto_break_check.isChecked()
        settings.auto_start_focus = self.auto_focus_check.isChecked()
        self.storage.save_settings(settings)

    @Slot(TimerContext)
    def _on_tick(self, context: TimerContext):
        """Handle timer tick - update display."""
        self.time_label.setText(context.format_remaining())
        
        # Update progress label
        if context.state != TimerState.IDLE:
            elapsed_min = context.elapsed_seconds // 60
            elapsed_sec = context.elapsed_seconds % 60
            total_min = context.total_seconds // 60
            self.progress_label.setText(
                f"{elapsed_min}:{elapsed_sec:02d} / {total_min}:00 "
                f"({context.progress_percentage:.0f}%)"
            )
        else:
            self.progress_label.setText("")

    @Slot(TimerState, TimerState)
    def _on_phase_changed(self, old_state: TimerState, new_state: TimerState):
        """Handle phase change - update UI state."""
        # Update phase label - bright colors for dark theme
        phase_colors = {
            TimerState.IDLE: ("#808080", "IDLE"),
            TimerState.FOCUS: ("#66BB6A", "FOCUS"),
            TimerState.BREAK: ("#42A5F5", "BREAK"),
            TimerState.PAUSED: ("#FFA726", "PAUSED"),
        }
        color, text = phase_colors.get(new_state, ("#808080", "IDLE"))
        self.phase_label.setText(text)
        self.phase_label.setStyleSheet(f"color: {color}; font-size: 20px;")
        self.time_label.setStyleSheet(f"color: {color}; font-size: 80px;")

        # Update buttons based on state
        if new_state == TimerState.IDLE:
            self.start_btn.setEnabled(True)
            self.start_btn.setText("Start Focus")
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText("Pause")
            self.stop_btn.setEnabled(False)
            self.skip_break_btn.setVisible(False)
            self.time_label.setText("00:00")
            self.progress_label.setText("")
            # Enable config controls
            self._set_config_enabled(True)
            
        elif new_state == TimerState.FOCUS:
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.pause_btn.setText("Pause")
            self.stop_btn.setEnabled(True)
            self.skip_break_btn.setVisible(False)
            # Disable config controls during focus
            self._set_config_enabled(False)
            
        elif new_state == TimerState.BREAK:
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.pause_btn.setText("Pause")
            self.stop_btn.setEnabled(True)
            self.skip_break_btn.setVisible(True)
            self._set_config_enabled(False)
            
        elif new_state == TimerState.PAUSED:
            self.pause_btn.setText("Resume")

    def _set_config_enabled(self, enabled: bool):
        """Enable/disable configuration controls."""
        self.group_combo.setEnabled(enabled)
        self.preset_combo.setEnabled(enabled)
        if enabled and self._use_custom:
            self.focus_spin.setEnabled(True)
            self.break_spin.setEnabled(True)
        elif not enabled:
            self.focus_spin.setEnabled(False)
            self.break_spin.setEnabled(False)
