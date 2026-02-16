"""
Notification module for the Focus Timer application.
Handles sound playback and desktop notifications on phase changes.
"""

import sys
import struct
import wave
import io
import os
import subprocess
from typing import Optional
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Slot
from PySide6.QtWidgets import QSystemTrayIcon
from PySide6.QtGui import QIcon


def generate_beep_wav(
    frequency: int = 800,
    duration_ms: int = 200,
    sample_rate: int = 44100,
    volume: float = 0.5
) -> bytes:
    """
    Generate a simple beep sound as WAV data.
    
    Args:
        frequency: Frequency of the beep in Hz.
        duration_ms: Duration of the beep in milliseconds.
        sample_rate: Sample rate (44100 is CD quality).
        volume: Volume level (0.0 to 1.0).
    
    Returns:
        WAV file data as bytes.
    """
    import math
    
    num_samples = int(sample_rate * duration_ms / 1000)
    max_amplitude = 32767 * volume
    
    samples = []
    for i in range(num_samples):
        # Generate sine wave
        t = i / sample_rate
        value = int(max_amplitude * math.sin(2 * math.pi * frequency * t))
        
        # Apply fade in/out to avoid clicks
        fade_samples = int(sample_rate * 0.01)  # 10ms fade
        if i < fade_samples:
            value = int(value * (i / fade_samples))
        elif i > num_samples - fade_samples:
            value = int(value * ((num_samples - i) / fade_samples))
        
        samples.append(struct.pack('<h', value))
    
    # Create WAV file in memory
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)  # Mono
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        wav.writeframes(b''.join(samples))
    
    return buffer.getvalue()


def generate_notification_sound() -> bytes:
    """Generate a pleasant notification sound (two-tone beep)."""
    import math
    
    sample_rate = 44100
    max_amplitude = 32767 * 0.4
    
    samples = []
    
    # First tone: 880 Hz for 100ms
    for i in range(int(sample_rate * 0.1)):
        t = i / sample_rate
        value = int(max_amplitude * math.sin(2 * math.pi * 880 * t))
        # Fade
        fade_samples = int(sample_rate * 0.01)
        if i < fade_samples:
            value = int(value * (i / fade_samples))
        elif i > int(sample_rate * 0.1) - fade_samples:
            value = int(value * ((int(sample_rate * 0.1) - i) / fade_samples))
        samples.append(value)
    
    # Short pause: 50ms
    samples.extend([0] * int(sample_rate * 0.05))
    
    # Second tone: 1046 Hz (C6) for 150ms
    for i in range(int(sample_rate * 0.15)):
        t = i / sample_rate
        value = int(max_amplitude * math.sin(2 * math.pi * 1046 * t))
        # Fade
        fade_samples = int(sample_rate * 0.015)
        if i < fade_samples:
            value = int(value * (i / fade_samples))
        elif i > int(sample_rate * 0.15) - fade_samples:
            value = int(value * ((int(sample_rate * 0.15) - i) / fade_samples))
        samples.append(value)
    
    # Create WAV file in memory
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(struct.pack(f'<{len(samples)}h', *samples))
    
    return buffer.getvalue()


class SoundPlayer:
    """
    Cross-platform sound player.
    Uses Qt multimedia for playback with fallbacks.
    """
    
    def __init__(self):
        self._enabled = True
        self._sound_data: Optional[bytes] = None
        self._temp_file: Optional[str] = None
        
        # Generate and cache the notification sound
        self._sound_data = generate_notification_sound()
        self._setup_temp_file()
    
    def _setup_temp_file(self):
        """Create a temporary file for the sound (needed for some playback methods)."""
        if self._sound_data is None:
            return
        
        import tempfile
        fd, self._temp_file = tempfile.mkstemp(suffix='.wav')
        with os.fdopen(fd, 'wb') as f:
            f.write(self._sound_data)
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
    
    def play(self):
        """Play the notification sound."""
        if not self._enabled or not self._temp_file:
            return
        
        try:
            self._play_sound()
        except Exception as e:
            print(f"Warning: Could not play sound: {e}")
    
    def _play_sound(self):
        """Platform-specific sound playback."""
        system = sys.platform.lower()
        
        if system == 'darwin':
            # macOS: use afplay
            subprocess.Popen(
                ['afplay', self._temp_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        elif system.startswith('linux'):
            # Linux: try paplay (PulseAudio), then aplay (ALSA)
            for cmd in ['paplay', 'aplay']:
                try:
                    subprocess.Popen(
                        [cmd, self._temp_file],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    return
                except FileNotFoundError:
                    continue
            # Fallback: try using pygame or other methods
            print("Warning: No audio player found (tried paplay, aplay)")
        elif system == 'win32':
            # Windows: use winsound
            import winsound
            winsound.PlaySound(self._temp_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
    
    def cleanup(self):
        """Clean up temporary files."""
        if self._temp_file and os.path.exists(self._temp_file):
            try:
                os.remove(self._temp_file)
            except Exception:
                pass


class NotificationManager(QObject):
    """
    Manages desktop notifications and sound alerts.
    Uses system tray for notifications.
    """
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._sound_player = SoundPlayer()
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._notification_enabled = True
        self._sound_enabled = True
    
    def set_tray_icon(self, tray_icon: QSystemTrayIcon):
        """Set the system tray icon for showing notifications."""
        self._tray_icon = tray_icon
    
    @property
    def notification_enabled(self) -> bool:
        return self._notification_enabled
    
    @notification_enabled.setter
    def notification_enabled(self, value: bool):
        self._notification_enabled = value
    
    @property
    def sound_enabled(self) -> bool:
        return self._sound_enabled
    
    @sound_enabled.setter
    def sound_enabled(self, value: bool):
        self._sound_enabled = value
        self._sound_player.enabled = value
    
    def notify_focus_start(self):
        """Notify that focus session has started."""
        self._play_sound()
        self._show_notification(
            "Focus Timer",
            "Focus session started. Stay focused! 🎯",
            QSystemTrayIcon.MessageIcon.Information
        )
    
    def notify_focus_complete(self):
        """Notify that focus session is complete."""
        self._play_sound()
        self._show_notification(
            "Focus Complete!",
            "Great work! Time for a break. ☕",
            QSystemTrayIcon.MessageIcon.Information
        )
    
    def notify_break_start(self):
        """Notify that break has started."""
        self._play_sound()
        self._show_notification(
            "Break Time",
            "Take a break and relax. 🌟",
            QSystemTrayIcon.MessageIcon.Information
        )
    
    def notify_break_complete(self):
        """Notify that break is complete."""
        self._play_sound()
        self._show_notification(
            "Break Over",
            "Ready for another focus session? 💪",
            QSystemTrayIcon.MessageIcon.Information
        )
    
    def _play_sound(self):
        """Play notification sound if enabled."""
        if self._sound_enabled:
            self._sound_player.play()
    
    def _show_notification(
        self, 
        title: str, 
        message: str, 
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information
    ):
        """Show a desktop notification."""
        if not self._notification_enabled:
            return
        
        if self._tray_icon is not None and QSystemTrayIcon.isSystemTrayAvailable():
            self._tray_icon.showMessage(title, message, icon, 3000)
        else:
            # Fallback: try native notification command
            self._show_native_notification(title, message)
    
    def _show_native_notification(self, title: str, message: str):
        """Show notification using native OS commands."""
        system = sys.platform.lower()
        
        try:
            if system == 'darwin':
                # macOS: use osascript
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(
                    ['osascript', '-e', script],
                    capture_output=True,
                    timeout=5
                )
            elif system.startswith('linux'):
                # Linux: use notify-send
                subprocess.run(
                    ['notify-send', title, message],
                    capture_output=True,
                    timeout=5
                )
            # Windows notifications handled by tray icon
        except Exception as e:
            print(f"Warning: Could not show notification: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        self._sound_player.cleanup()


# Global instance
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """Get or create the global NotificationManager instance."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager
