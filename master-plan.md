## Project Overview
ActivityBeacon is a macOS-native screenshot automation tool that captures multi-monitor screenshots, tracks window focus, and generates timelapse videos. The project consists of three main components:
- **Capture daemon**: macOS menu bar app using `PyQt6` that periodically captures screenshots
- **Timelapse generator**: Creates MP4 videos from daily screenshots using `ffmpeg`
- **Viewer GUI** (`viewer/` module): PyQt6 app for reviewing daily timelapses with focus timeline

## Architecture

### Data Storage Format
Screenshots and metadata are stored in a date-based hierarchy:
```
~/Documents/Screenshots/YYYY/MM/DD/
  ├── YYYYMMDD_HHMMSS.png    # Screenshots with change detection
  ├── window_data.jsonl       # One JSON object per line (not an array!)
  └── timelapse-YYYYMMDD.mp4 # Generated video (optional)
```

**Critical**: `window_data.jsonl` uses newline-delimited JSON (JSONL), not a JSON array. Each line is a complete JSON object with:
- `timestamp`: ISO format datetime
- `focused_app_name`, `focused_app_pid`, `focused_window_name`: Active application metadata
- `windows`: Array of all visible windows with `app_name`, `window_name`, `owner_pid`, `is_active`, `is_focused_window`

### Multi-Monitor Handling
The screenshot pipeline
1. Captures each monitor separately using `mss`
2. Scales images to match highest resolution (preserves aspect ratio)
3. Stitches horizontally left-to-right into a single wide image
4. Only saves if pixel difference threshold exceeded (change detection via numpy array diff)

### macOS Integration
Uses PyObjC frameworks directly:
- `AppKit.NSWorkspace` for active application detection (PID-based focus tracking)
- `Quartz.CGWindowListCopyWindowInfo` for all on-screen windows
- `Quartz.CGSessionCopyCurrentDictionary` for screen lock detection (pauses capture when locked)
- Menu bar icon via `PyQt6` with scheduling controls

## Development Workflows

### Setup & Dependencies
```bash
make setup      # Create virtualenv
make deps       # Install requirements.txt and requirements-dev.txt
make pre-commit # Run linting/formatting hooks
```

### Building macOS App Bundle
```bash
make package           # Creates .app using PyInstaller (main.spec)
make install-macosx    # Copies to ~/Applications
```

The main.spec file includes critical configuration:
- `entitlements.plist` provides screen recording permissions
- One-file bundle for easy distribution

### Running Components
```bash
make run          # Start screenshot daemon (menu bar app)
make run-ui        # Launch PyQt6 viewer GUI
```

### Timelapse Generation
Single date: `make timelapse DATE=2025-10-21 FPS=24 OVERWRITE=true DELETE=true`
All dates: `make timelapses FPS=30 OVERWRITE=true`

**Flags**:
- `OVERWRITE=true`: Regenerate existing videos
- `DELETE=true`: Remove source screenshots after successful encoding
- Default FPS is 30, output goes to same date directory

Batch script `scripts/generate_timelapses.sh` walks the date hierarchy and invokes `timelapse.py` for each day.

## Code Conventions

### Viewer Module Structure
The `viewer/` package uses Qt's MVC pattern:
- **FileSystemReader**: Scans date directories, validates structure
- **WindowDataParser**: Parses JSONL, creates `WindowDataEntry` dataclasses
- **CalendarWidget**: Custom QCalendarWidget with visual indicators (blue dot = screenshots, green bold = video exists)
- **VideoPlayerWidget**, **WindowDataTimeline**: Video playback and focus event timeline display

Each component communicates via PyQt signals (e.g., `date_selected`, `error_occurred`, `loading_started/finished`).

### Error Handling Patterns
- File I/O wraps `OSError` and `PermissionError` with user-friendly error messages stored in `last_error_msg` attributes
- Logging to `~/.logs/snap_span/snap_scan_YYYYMMDD.log`
- Screen lock detection silently skips captures rather than failing

### Logging
Custom logger setup:
- Daily rotating log files in `~/.logs/snap_span/`
- Both file and console handlers
- Format: `YYYY-MM-DD HH:MM:SS - LEVEL - message`

## External Dependencies

### Required System Tools
- **ffmpeg**: Must be on PATH for timelapse generation (installed via `brew install ffmpeg` on macOS)
- Checked at runtime using `shutil.which("ffmpeg")`

### Python Package Notes
- `PyQt6`: GUI framework for menu bar app and viewer app
- `mss`: Fast multi-platform screenshot library
- `screeninfo`: Monitor detection and geometry
- `Pillow`: Image manipulation (scaling, stitching, optimization)

## Common Pitfalls

1. **JSONL parsing**: Do NOT use `json.load()` on `window_data.jsonl`—it's not a JSON array. Use line-by-line `json.loads()`.
2. **Date directory format**: Always zero-padded (YYYY/MM/DD, e.g., 2025/01/05 not 2025/1/5).
3. **PyInstaller hidden imports**: `PyQt6` requires explicit hidden imports in spec file.
4. **Screen lock behavior**: Captures pause when screen locked (via `is_screen_locked()` check).
5. **Change detection threshold**: `np.max(diff) > 10`—adjust if too sensitive.

## Testing & Debugging

- Test multi-monitor behavior by disconnecting/reconnecting displays during capture
- Viewer errors often stem from malformed JSONL—validate with `jq` or Python REPL
- Use `make pre-commit-tool TOOL=<hook>` to run individual linters
