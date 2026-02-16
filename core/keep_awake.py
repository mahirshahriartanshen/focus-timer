"""
Cross-platform screen awake functionality.
Prevents the screen from going to sleep while the focus timer is running.

Implementations:
    - Windows: ctypes + SetThreadExecutionState
    - macOS: caffeinate subprocess
    - Linux: systemd-inhibit or xdg-screensaver reset fallback
"""

import os
import sys
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from typing import Optional


class KeepAwakeBase(ABC):
    """Abstract base class for keep-awake implementations."""
    
    @abstractmethod
    def start(self):
        """Start keeping the screen awake."""
        pass
    
    @abstractmethod
    def stop(self):
        """Stop keeping the screen awake."""
        pass
    
    @abstractmethod
    def is_active(self) -> bool:
        """Check if keep-awake is currently active."""
        pass


class WindowsKeepAwake(KeepAwakeBase):
    """
    Windows implementation using SetThreadExecutionState.
    Uses ctypes to call the Windows API directly.
    """
    
    # Execution state flags
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    
    def __init__(self):
        self._active = False
        self._kernel32 = None
        
    def _load_kernel32(self):
        """Load kernel32.dll if not already loaded."""
        if self._kernel32 is None:
            import ctypes
            self._kernel32 = ctypes.windll.kernel32
    
    def start(self):
        """Start preventing sleep by setting execution state."""
        if self._active:
            return
        
        try:
            self._load_kernel32()
            # Request the system and display stay on
            self._kernel32.SetThreadExecutionState(
                self.ES_CONTINUOUS | 
                self.ES_SYSTEM_REQUIRED | 
                self.ES_DISPLAY_REQUIRED
            )
            self._active = True
        except Exception as e:
            print(f"Warning: Could not enable keep-awake on Windows: {e}")
    
    def stop(self):
        """Allow sleep by resetting execution state."""
        if not self._active:
            return
        
        try:
            self._load_kernel32()
            # Reset to default (allow sleep)
            self._kernel32.SetThreadExecutionState(self.ES_CONTINUOUS)
            self._active = False
        except Exception as e:
            print(f"Warning: Could not disable keep-awake on Windows: {e}")
    
    def is_active(self) -> bool:
        return self._active


class MacOSKeepAwake(KeepAwakeBase):
    """
    macOS implementation using caffeinate subprocess.
    caffeinate is a built-in macOS utility that prevents sleep.
    """
    
    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
    
    def start(self):
        """Start caffeinate subprocess."""
        if self._process is not None:
            return
        
        try:
            # -d: prevent display sleep
            # -i: prevent system idle sleep
            self._process = subprocess.Popen(
                ['caffeinate', '-d', '-i'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            print("Warning: caffeinate not found on this macOS system")
        except Exception as e:
            print(f"Warning: Could not start caffeinate: {e}")
    
    def stop(self):
        """Stop caffeinate subprocess."""
        if self._process is None:
            return
        
        try:
            self._process.terminate()
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._process.kill()
        except Exception as e:
            print(f"Warning: Error stopping caffeinate: {e}")
        finally:
            self._process = None
    
    def is_active(self) -> bool:
        return self._process is not None and self._process.poll() is None


class LinuxKeepAwake(KeepAwakeBase):
    """
    Linux implementation with multiple strategies for maximum compatibility:
    1. systemd-inhibit (inhibit idle AND sleep)
    2. xset to disable screensaver
    3. xdg-screensaver reset (periodic)
    4. Simulate activity with xdotool (if available)
    
    Uses multiple methods simultaneously for reliability.
    """
    
    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._keep_alive_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._xset_disabled = False
        self._active = False
    
    def _check_command_exists(self, command: str) -> bool:
        """Check if a command exists on the system."""
        try:
            result = subprocess.run(
                ['which', command],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _run_command(self, cmd: list, timeout: int = 5) -> bool:
        """Run a command silently, return success status."""
        try:
            subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout
            )
            return True
        except Exception:
            return False
    
    def start(self):
        """Start keeping screen awake using all available methods."""
        if self._active:
            return
        
        self._active = True
        self._stop_event.clear()
        
        # Method 1: Try systemd-inhibit to block idle and sleep
        if self._check_command_exists('systemd-inhibit'):
            try:
                self._process = subprocess.Popen(
                    [
                        'systemd-inhibit',
                        '--what=idle:sleep',
                        '--who=FocusTimer',
                        '--why=Focus session in progress',
                        '--mode=block',
                        'sleep', 'infinity'
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception as e:
                print(f"Warning: systemd-inhibit failed: {e}")
        
        # Method 2: Disable screensaver via xset
        if self._check_command_exists('xset'):
            try:
                # Disable screen saver
                self._run_command(['xset', 's', 'off'])
                # Disable DPMS (Display Power Management)
                self._run_command(['xset', '-dpms'])
                self._xset_disabled = True
            except Exception:
                pass
        
        # Method 3: Start background thread for periodic resets
        self._keep_alive_thread = threading.Thread(
            target=self._keep_alive_loop, 
            daemon=True
        )
        self._keep_alive_thread.start()
    
    def _keep_alive_loop(self):
        """
        Periodic loop to keep screen awake using multiple methods.
        Runs every 30 seconds while active.
        """
        has_xdg = self._check_command_exists('xdg-screensaver')
        has_xdotool = self._check_command_exists('xdotool')
        has_dbus = self._check_command_exists('dbus-send')
        
        while not self._stop_event.is_set():
            # Method A: Reset xdg-screensaver
            if has_xdg:
                self._run_command(['xdg-screensaver', 'reset'])
            
            # Method B: Simulate tiny mouse movement with xdotool
            # This is very effective at preventing sleep
            if has_xdotool:
                # Move mouse 0 pixels (just resets idle timer)
                self._run_command(['xdotool', 'mousemove_relative', '0', '0'])
            
            # Method C: Send inhibit signal via D-Bus (GNOME/KDE)
            if has_dbus:
                # Try GNOME screensaver inhibit
                self._run_command([
                    'dbus-send', '--session', '--type=method_call',
                    '--dest=org.gnome.ScreenSaver',
                    '/org/gnome/ScreenSaver',
                    'org.gnome.ScreenSaver.SimulateUserActivity'
                ])
                # Try freedesktop screensaver
                self._run_command([
                    'dbus-send', '--session', '--type=method_call',
                    '--dest=org.freedesktop.ScreenSaver',
                    '/org/freedesktop/ScreenSaver',
                    'org.freedesktop.ScreenSaver.SimulateUserActivity'
                ])
            
            # Wait 30 seconds before next reset
            self._stop_event.wait(30)
    
    def stop(self):
        """Stop keeping screen awake and restore settings."""
        if not self._active:
            return
        
        self._active = False
        
        # Stop the keep-alive thread
        self._stop_event.set()
        if self._keep_alive_thread is not None:
            self._keep_alive_thread.join(timeout=5)
            self._keep_alive_thread = None
        
        # Stop systemd-inhibit process
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            except Exception as e:
                print(f"Warning: Error stopping systemd-inhibit: {e}")
            finally:
                self._process = None
        
        # Re-enable screensaver via xset
        if self._xset_disabled and self._check_command_exists('xset'):
            try:
                # Re-enable screen saver
                self._run_command(['xset', 's', 'on'])
                # Re-enable DPMS
                self._run_command(['xset', '+dpms'])
            except Exception:
                pass
            self._xset_disabled = False
    
    def is_active(self) -> bool:
        return self._active


class DummyKeepAwake(KeepAwakeBase):
    """Dummy implementation for unsupported platforms."""
    
    def __init__(self):
        self._active = False
    
    def start(self):
        self._active = True
        print("Warning: Keep-awake not supported on this platform")
    
    def stop(self):
        self._active = False
    
    def is_active(self) -> bool:
        return self._active


class KeepAwakeManager:
    """
    Manager class that selects and manages the appropriate 
    keep-awake implementation for the current platform.
    """
    
    def __init__(self):
        """Initialize with platform-appropriate implementation."""
        self._impl = self._create_implementation()
        self._enabled = True
    
    def _create_implementation(self) -> KeepAwakeBase:
        """Create the appropriate implementation for the current OS."""
        system = sys.platform.lower()
        
        if system == 'win32' or system == 'cygwin':
            return WindowsKeepAwake()
        elif system == 'darwin':
            return MacOSKeepAwake()
        elif system.startswith('linux') or system == 'linux2':
            return LinuxKeepAwake()
        else:
            return DummyKeepAwake()
    
    @property
    def enabled(self) -> bool:
        """Check if keep-awake is enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        """Enable or disable keep-awake functionality."""
        self._enabled = value
        if not value and self._impl.is_active():
            self._impl.stop()
    
    def start(self):
        """Start keeping the screen awake (if enabled)."""
        if self._enabled:
            self._impl.start()
    
    def stop(self):
        """Stop keeping the screen awake."""
        self._impl.stop()
    
    def is_active(self) -> bool:
        """Check if keep-awake is currently active."""
        return self._impl.is_active()
    
    def cleanup(self):
        """
        Cleanup resources. 
        Should be called before application exit.
        """
        self._impl.stop()


# Global instance for convenient access
_keep_awake_manager: Optional[KeepAwakeManager] = None


def get_keep_awake_manager() -> KeepAwakeManager:
    """Get or create the global KeepAwakeManager instance."""
    global _keep_awake_manager
    if _keep_awake_manager is None:
        _keep_awake_manager = KeepAwakeManager()
    return _keep_awake_manager
