"""
Data models for the Focus Timer application.
Uses dataclasses for clean, type-annotated data structures.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
import time


class TimerState(Enum):
    """Possible states for the timer state machine."""
    IDLE = auto()
    FOCUS = auto()
    BREAK = auto()
    PAUSED = auto()


class SessionStatus(Enum):
    """Status of a completed session."""
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"


@dataclass
class Group:
    """
    Represents a category/group for organizing focus sessions.
    Examples: Study, Work, Coding, Reading, etc.
    """
    id: Optional[int] = None
    name: str = ""
    default_focus_minutes: int = 25
    default_break_minutes: int = 5
    color: str = "#4CAF50"  # Default green color
    created_at: int = field(default_factory=lambda: int(time.time()))

    def __post_init__(self):
        """Validate group data."""
        if self.default_focus_minutes < 1:
            self.default_focus_minutes = 1
        if self.default_break_minutes < 1:
            self.default_break_minutes = 1


@dataclass
class Session:
    """
    Represents a focus or break session record.
    Stored in the database for history tracking.
    """
    id: Optional[int] = None
    group_id: int = 0
    start_ts: int = 0  # Unix timestamp when session started
    end_ts: int = 0    # Unix timestamp when session ended
    planned_seconds: int = 0  # Originally planned duration
    actual_seconds: int = 0   # Actual time spent (may differ if interrupted)
    status: str = SessionStatus.COMPLETED.value
    note: Optional[str] = None
    created_at: int = field(default_factory=lambda: int(time.time()))
    is_break: bool = False  # True if this was a break session

    @property
    def duration_minutes(self) -> float:
        """Return actual duration in minutes."""
        return self.actual_seconds / 60.0

    @property
    def completion_percentage(self) -> float:
        """Return percentage of planned time completed."""
        if self.planned_seconds == 0:
            return 0.0
        return min(100.0, (self.actual_seconds / self.planned_seconds) * 100.0)


@dataclass
class TimerPreset:
    """Predefined timer configuration."""
    name: str
    focus_minutes: int
    break_minutes: int

    def __str__(self) -> str:
        return f"{self.name} ({self.focus_minutes}/{self.break_minutes})"


# Default presets available in the application
DEFAULT_PRESETS = [
    TimerPreset("Classic Pomodoro", 25, 5),
    TimerPreset("Extended Focus", 50, 10),
    TimerPreset("Long Session", 60, 15),
    TimerPreset("Deep Work", 90, 20),
]


@dataclass
class AppSettings:
    """Application settings stored in database or config."""
    auto_start_break: bool = True
    auto_start_focus: bool = False
    keep_screen_awake: bool = True
    sound_enabled: bool = True
    notification_enabled: bool = True
    log_breaks: bool = False  # Whether to log break sessions


@dataclass
class TimerContext:
    """
    Current timer context containing all state information.
    Used to pass timer state to UI components.
    """
    state: TimerState = TimerState.IDLE
    remaining_seconds: int = 0
    total_seconds: int = 0
    current_group_id: Optional[int] = None
    focus_minutes: int = 25
    break_minutes: int = 5
    session_start_ts: int = 0
    pause_start_ts: int = 0
    total_paused_seconds: int = 0

    @property
    def elapsed_seconds(self) -> int:
        """Calculate elapsed seconds in current session."""
        return self.total_seconds - self.remaining_seconds

    @property
    def progress_percentage(self) -> float:
        """Return progress as percentage (0-100)."""
        if self.total_seconds == 0:
            return 0.0
        return ((self.total_seconds - self.remaining_seconds) / self.total_seconds) * 100.0

    def format_remaining(self) -> str:
        """Format remaining time as MM:SS."""
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
