"""
Timer engine for the Focus Timer application.
Implements a robust state machine for managing timer states.
Uses timestamp-based calculations to prevent drift.
"""

import time
from typing import Optional, Callable
from PySide6.QtCore import QObject, QTimer, Signal

from .models import TimerState, TimerContext, Session, SessionStatus
from .storage import Storage


class TimerEngine(QObject):
    """
    Core timer engine implementing a state machine.
    
    States:
        IDLE: No timer running
        FOCUS: Focus session in progress
        BREAK: Break session in progress
        PAUSED: Timer paused (can resume)
    
    Signals:
        tick: Emitted every tick with current TimerContext
        phase_changed: Emitted when state changes (provides old_state, new_state)
        session_completed: Emitted when a session finishes (provides Session object)
    """

    # Signals
    tick = Signal(TimerContext)
    phase_changed = Signal(TimerState, TimerState)  # old_state, new_state
    session_completed = Signal(Session)

    # Tick interval in milliseconds (200-500ms as specified)
    TICK_INTERVAL_MS = 300

    def __init__(self, storage: Storage, parent: Optional[QObject] = None):
        """
        Initialize the timer engine.
        
        Args:
            storage: Storage instance for saving sessions.
            parent: Optional Qt parent object.
        """
        super().__init__(parent)
        
        self.storage = storage
        
        # Timer context (current state)
        self._context = TimerContext()
        
        # State before pause (to restore after resume)
        self._state_before_pause: Optional[TimerState] = None
        
        # Qt timer for UI updates
        self._qt_timer = QTimer(self)
        self._qt_timer.setInterval(self.TICK_INTERVAL_MS)
        self._qt_timer.timeout.connect(self._on_tick)
        
        # Session tracking
        self._current_session_start: int = 0
        self._current_planned_seconds: int = 0

    @property
    def context(self) -> TimerContext:
        """Get current timer context."""
        return self._context

    @property
    def state(self) -> TimerState:
        """Get current timer state."""
        return self._context.state

    @property
    def is_running(self) -> bool:
        """Check if timer is actively running (not paused or idle)."""
        return self._context.state in (TimerState.FOCUS, TimerState.BREAK)

    @property
    def is_focus(self) -> bool:
        """Check if currently in focus mode."""
        return self._context.state == TimerState.FOCUS

    @property
    def is_break(self) -> bool:
        """Check if currently in break mode."""
        return self._context.state == TimerState.BREAK

    @property
    def is_paused(self) -> bool:
        """Check if timer is paused."""
        return self._context.state == TimerState.PAUSED

    @property
    def is_idle(self) -> bool:
        """Check if timer is idle."""
        return self._context.state == TimerState.IDLE

    def start_focus(
        self,
        focus_minutes: int,
        break_minutes: int,
        group_id: Optional[int] = None
    ):
        """
        Start a new focus session.
        
        Args:
            focus_minutes: Duration of focus period in minutes.
            break_minutes: Duration of break period in minutes.
            group_id: Optional group ID for this session.
        """
        # Stop any existing session
        if not self.is_idle:
            self._stop_and_save(interrupted=True)
        
        # Update context
        old_state = self._context.state
        self._context.state = TimerState.FOCUS
        self._context.focus_minutes = focus_minutes
        self._context.break_minutes = break_minutes
        self._context.current_group_id = group_id
        self._context.total_seconds = focus_minutes * 60
        self._context.remaining_seconds = self._context.total_seconds
        self._context.session_start_ts = int(time.time())
        self._context.total_paused_seconds = 0
        
        # Track session for saving
        self._current_session_start = self._context.session_start_ts
        self._current_planned_seconds = self._context.total_seconds
        
        # Start the timer
        self._qt_timer.start()
        
        # Emit state change
        self.phase_changed.emit(old_state, TimerState.FOCUS)
        self.tick.emit(self._context)

    def start_break(self):
        """Start the break period after focus."""
        old_state = self._context.state
        
        # Save focus session if we were in focus
        if old_state == TimerState.FOCUS:
            self._save_session(completed=True, is_break=False)
        
        # Update context for break
        self._context.state = TimerState.BREAK
        self._context.total_seconds = self._context.break_minutes * 60
        self._context.remaining_seconds = self._context.total_seconds
        self._context.session_start_ts = int(time.time())
        self._context.total_paused_seconds = 0
        
        # Track break session
        self._current_session_start = self._context.session_start_ts
        self._current_planned_seconds = self._context.total_seconds
        
        # Start/continue the timer
        if not self._qt_timer.isActive():
            self._qt_timer.start()
        
        # Emit state change
        self.phase_changed.emit(old_state, TimerState.BREAK)
        self.tick.emit(self._context)

    def pause(self):
        """Pause the current timer."""
        if not self.is_running:
            return
        
        old_state = self._context.state
        self._state_before_pause = old_state
        self._context.state = TimerState.PAUSED
        self._context.pause_start_ts = int(time.time())
        
        # Stop the ticker (but don't save session yet)
        self._qt_timer.stop()
        
        # Emit state change
        self.phase_changed.emit(old_state, TimerState.PAUSED)
        self.tick.emit(self._context)

    def resume(self):
        """Resume from paused state."""
        if not self.is_paused or self._state_before_pause is None:
            return
        
        # Calculate how long we were paused
        pause_duration = int(time.time()) - self._context.pause_start_ts
        self._context.total_paused_seconds += pause_duration
        
        # Restore previous state
        old_state = TimerState.PAUSED
        self._context.state = self._state_before_pause
        self._state_before_pause = None
        self._context.pause_start_ts = 0
        
        # Restart the ticker
        self._qt_timer.start()
        
        # Emit state change
        self.phase_changed.emit(old_state, self._context.state)
        self.tick.emit(self._context)

    def stop(self):
        """Stop the timer and save session as interrupted."""
        if self.is_idle:
            return
        
        self._stop_and_save(interrupted=True)

    def skip_break(self):
        """Skip the current break and return to idle."""
        if not self.is_break:
            return
        
        old_state = self._context.state
        self._qt_timer.stop()
        
        # Save break session if logging breaks is enabled
        settings = self.storage.get_settings()
        if settings.log_breaks:
            self._save_session(completed=False, is_break=True)
        
        # Reset to idle
        self._reset_to_idle()
        
        # Emit state change
        self.phase_changed.emit(old_state, TimerState.IDLE)
        self.tick.emit(self._context)

    def _on_tick(self):
        """
        Handle timer tick.
        Calculates remaining time based on timestamps for accuracy.
        """
        if not self.is_running:
            return
        
        # Calculate elapsed time from timestamps (prevents drift)
        now = int(time.time())
        elapsed = now - self._context.session_start_ts - self._context.total_paused_seconds
        self._context.remaining_seconds = max(0, self._context.total_seconds - elapsed)
        
        # Emit tick for UI update
        self.tick.emit(self._context)
        
        # Check if time is up
        if self._context.remaining_seconds <= 0:
            self._on_phase_complete()

    def _on_phase_complete(self):
        """Handle completion of current phase."""
        self._qt_timer.stop()
        
        if self.is_focus:
            # Focus session completed
            self._save_session(completed=True, is_break=False)
            
            # Check if we should auto-start break
            settings = self.storage.get_settings()
            if settings.auto_start_break:
                self.start_break()
            else:
                old_state = self._context.state
                self._reset_to_idle()
                self.phase_changed.emit(old_state, TimerState.IDLE)
                
        elif self.is_break:
            # Break completed
            settings = self.storage.get_settings()
            if settings.log_breaks:
                self._save_session(completed=True, is_break=True)
            
            # Check if we should auto-start focus
            if settings.auto_start_focus:
                self.start_focus(
                    self._context.focus_minutes,
                    self._context.break_minutes,
                    self._context.current_group_id
                )
            else:
                old_state = self._context.state
                self._reset_to_idle()
                self.phase_changed.emit(old_state, TimerState.IDLE)

    def _stop_and_save(self, interrupted: bool):
        """Stop timer and save session."""
        self._qt_timer.stop()
        
        # Determine if this was a break or focus session
        was_focus = self._context.state == TimerState.FOCUS or (
            self._context.state == TimerState.PAUSED and 
            self._state_before_pause == TimerState.FOCUS
        )
        was_break = self._context.state == TimerState.BREAK or (
            self._context.state == TimerState.PAUSED and 
            self._state_before_pause == TimerState.BREAK
        )
        
        old_state = self._context.state
        
        if was_focus:
            self._save_session(completed=not interrupted, is_break=False)
        elif was_break:
            settings = self.storage.get_settings()
            if settings.log_breaks:
                self._save_session(completed=not interrupted, is_break=True)
        
        self._reset_to_idle()
        self.phase_changed.emit(old_state, TimerState.IDLE)
        self.tick.emit(self._context)

    def _save_session(self, completed: bool, is_break: bool):
        """Save the current session to storage."""
        now = int(time.time())
        
        # Calculate actual seconds (accounting for pauses)
        if self._context.pause_start_ts > 0:
            # Currently paused
            actual_seconds = (
                self._context.pause_start_ts - 
                self._current_session_start - 
                self._context.total_paused_seconds
            )
        else:
            actual_seconds = (
                now - 
                self._current_session_start - 
                self._context.total_paused_seconds
            )
        
        # Ensure actual_seconds is non-negative and within bounds
        actual_seconds = max(0, min(actual_seconds, self._current_planned_seconds))
        
        session = Session(
            group_id=self._context.current_group_id or 0,
            start_ts=self._current_session_start,
            end_ts=now,
            planned_seconds=self._current_planned_seconds,
            actual_seconds=actual_seconds,
            status=SessionStatus.COMPLETED.value if completed else SessionStatus.INTERRUPTED.value,
            is_break=is_break
        )
        
        # Save to database
        session_id = self.storage.create_session(session)
        session.id = session_id
        
        # Emit signal
        self.session_completed.emit(session)

    def _reset_to_idle(self):
        """Reset context to idle state."""
        self._context.state = TimerState.IDLE
        self._context.remaining_seconds = 0
        self._context.total_seconds = 0
        self._context.session_start_ts = 0
        self._context.pause_start_ts = 0
        self._context.total_paused_seconds = 0
        self._state_before_pause = None
        self._current_session_start = 0
        self._current_planned_seconds = 0

    def cleanup(self):
        """Cleanup resources. Call before application exit."""
        if self.is_running or self.is_paused:
            self._stop_and_save(interrupted=True)
        self._qt_timer.stop()
