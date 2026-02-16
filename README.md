# Focus Timer

A local-only Pomodoro-style focus timer application built with PySide6 (Qt) and SQLite.

![Focus Timer](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/GUI-PySide6-green.svg)
![SQLite](https://img.shields.io/badge/Storage-SQLite-lightgrey.svg)

## Features

- **Timer Presets**: Classic Pomodoro (25/5), Extended (50/10), Long (60/15), Deep Work (90/20), and Custom
- **Categories/Groups**: Organize sessions by category (Study, Work, Coding, etc.) with custom colors
- **Session History**: Track all focus sessions with filtering by date and category
- **Statistics**: View daily/weekly totals and per-category breakdowns
- **CSV Export**: Export session history for external analysis
- **Desktop Notifications**: Get notified when phases change
- **Sound Alerts**: Pleasant audio notification on phase transitions
- **Screen Awake**: Prevent screen sleep during focus sessions (cross-platform)
- **System Tray**: Minimize to tray, control timer from tray menu
- **Local-Only**: No cloud, no tracking, all data stored locally

## Requirements

- Python 3.8+
- Windows / Linux / macOS
- Dependencies listed in requirements.txt

---

## Installation & Run

### 1) Clone the repository

git clone https://github.com/mahirshahriartanshen/focus-timer.git  
cd focus-timer  

### 2) (Recommended) Create virtual environment

###Linux / macOS:

python3 -m venv venv  
source venv/bin/activate  

###Windows:

python -m venv venv  
venv\Scripts\activate  

## Project Structure

```
focus_timer/
├── main.py                 # Application entry point
├── core/
│   ├── __init__.py
│   ├── models.py          # Data models (Group, Session, etc.)
│   ├── storage.py         # SQLite database operations
│   ├── timer_engine.py    # Timer state machine
│   ├── keep_awake.py      # Screen awake functionality
│   └── notifications.py   # Sound and desktop notifications
└── ui/
    ├── __init__.py
    ├── main_window.py     # Main application window
    ├── timer_page.py      # Timer tab with controls
    ├── history_page.py    # Session history and statistics
    ├── groups_page.py     # Category management
    └── settings_page.py   # Application settings
```

## Usage

### Timer Page

1. Select a **Category** (e.g., Study, Work, Coding)
2. Choose a **Preset** or select "Custom" to set your own durations
3. Click **Start Focus** to begin
4. Use **Pause/Resume** as needed
5. When focus ends, break starts automatically (configurable)

### Categories

- Create custom categories with unique colors
- Set default focus/break durations per category
- Delete categories (and associated sessions)

### History

- View all completed focus sessions
- Filter by date range and category
- See daily and weekly totals
- Export data to CSV

### Settings

- **Auto-start break**: Automatically start break after focus
- **Auto-start focus**: Automatically start focus after break
- **Sound**: Play notification sounds
- **Notifications**: Show desktop notifications
- **Keep screen awake**: Prevent sleep during focus
- **Log breaks**: Include break sessions in history

## Data Storage

Session data is stored in a SQLite database in your user data folder:
- **Linux**: `~/.local/share/FocusTimer/focus_timer.db`
- **macOS**: `~/Library/Application Support/FocusTimer/focus_timer.db`
- **Windows**: `%APPDATA%/FocusTimer/focus_timer.db`

## Platform Support

### Keep Screen Awake
- **Windows**: Uses `SetThreadExecutionState` via ctypes
- **macOS**: Uses the `caffeinate` command
- **Linux**: Uses multiple methods for maximum compatibility:
  - `systemd-inhibit` (inhibits idle and sleep)
  - `xset` (disables screensaver and DPMS)
  - `xdg-screensaver reset` (periodic reset)
  - `xdotool` (simulates activity - most effective)
  - `dbus-send` (GNOME/KDE screensaver inhibit)

  For best results on Linux, install `xdotool`:
  ```bash
  # Debian/Ubuntu/Kali
  sudo apt install xdotool
  
  # Fedora
  sudo dnf install xdotool
  
  # Arch
  sudo pacman -S xdotool
  ```

### Sound Notifications
- **Windows**: Uses `winsound`
- **macOS**: Uses `afplay`
- **Linux**: Uses `paplay` (PulseAudio) or `aplay` (ALSA)

### Desktop Notifications
- Uses Qt's `QSystemTrayIcon` for cross-platform notifications
- Fallback to native notification commands (`notify-send`, `osascript`)

## License

MIT License - Feel free to use and modify as needed.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
