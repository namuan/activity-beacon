# Requirements Document

## Introduction

ActivityBeacon is a macOS-native screenshot automation tool that captures multi-monitor screenshots, tracks window focus, and generates timelapse videos. The system provides automated screenshot capture with change detection, window focus tracking, and video generation capabilities for productivity monitoring and review.

## Glossary

- **Capture_Daemon**: The macOS menu bar application that periodically captures screenshots
- **Timelapse_Generator**: The component that creates MP4 videos from daily screenshots
- **Viewer_GUI**: The PyQt6 application for reviewing daily timelapses with focus timeline
- **Screenshot_Pipeline**: The multi-monitor screenshot capture and processing system
- **Window_Data**: Metadata about active applications and visible windows
- **Change_Detection**: Algorithm that determines if a screenshot differs significantly from the previous one
- **JSONL_Format**: Newline-delimited JSON format where each line is a complete JSON object
- **Focus_Timeline**: Visual representation of window focus events over time

## Requirements

### Requirement 1: Screenshot Capture System

**User Story:** As a productivity tracker, I want to automatically capture screenshots of my desktop, so that I can review my work activity over time.

#### Acceptance Criteria

1. WHEN the capture daemon is running, THE Screenshot_Pipeline SHALL capture screenshots from all connected monitors every configurable interval
2. WHEN multiple monitors are connected, THE Screenshot_Pipeline SHALL stitch them horizontally into a single wide image
3. WHEN capturing multi-monitor setups, THE Screenshot_Pipeline SHALL scale images to match the highest resolution while preserving aspect ratio
4. WHEN a new screenshot is captured, THE Change_Detection SHALL compare it with the previous screenshot using pixel difference analysis
5. WHEN the pixel difference exceeds a threshold of 10, THE Screenshot_Pipeline SHALL save the screenshot to disk
6. WHEN the pixel difference is below the threshold, THE Screenshot_Pipeline SHALL discard the screenshot to save storage space

### Requirement 2: Window Focus Tracking

**User Story:** As a productivity analyst, I want to track which applications and windows are active, so that I can understand my focus patterns and application usage.

#### Acceptance Criteria

1. WHEN a screenshot is captured, THE Window_Data SHALL record the currently focused application name, PID, and window name
2. WHEN collecting window data, THE Window_Data SHALL enumerate all visible windows with their application names, window names, owner PIDs, active status, and focus status
3. WHEN storing window metadata, THE Window_Data SHALL write each entry as a separate JSON object on its own line in JSONL format
4. WHEN recording timestamps, THE Window_Data SHALL use ISO format datetime for all timestamp entries
5. THE Window_Data SHALL NOT store window information as a JSON array but as newline-delimited JSON objects

### Requirement 3: Data Storage and Organization

**User Story:** As a user reviewing my activity, I want screenshots and metadata organized by date, so that I can easily find and review specific days.

#### Acceptance Criteria

1. WHEN storing screenshots, THE Capture_Daemon SHALL organize files in a date-based hierarchy: ~/Documents/Screenshots/YYYY/MM/DD/
2. WHEN saving screenshots, THE Capture_Daemon SHALL use the filename format YYYYMMDD_HHMMSS.png
3. WHEN storing window data, THE Capture_Daemon SHALL save it as window_data.jsonl in the same date directory
4. WHEN creating date directories, THE Capture_Daemon SHALL use zero-padded format (e.g., 2025/01/05 not 2025/1/5)
5. THE Capture_Daemon SHALL ensure each date directory contains screenshots, window data, and optionally generated timelapse videos

### Requirement 4: macOS System Integration

**User Story:** As a macOS user, I want the application to integrate seamlessly with the operating system, so that it works reliably with system features like screen locking and application switching.

#### Acceptance Criteria

1. WHEN detecting the active application, THE Capture_Daemon SHALL use AppKit.NSWorkspace for PID-based focus tracking
2. WHEN enumerating windows, THE Capture_Daemon SHALL use Quartz.CGWindowListCopyWindowInfo for all on-screen windows
3. WHEN the screen is locked, THE Capture_Daemon SHALL pause screenshot capture using Quartz.CGSessionCopyCurrentDictionary detection
4. WHEN the screen becomes unlocked, THE Capture_Daemon SHALL resume screenshot capture automatically
5. THE Capture_Daemon SHALL provide a menu bar icon using PyQt6 with scheduling controls

### Requirement 5: Timelapse Video Generation

**User Story:** As a user reviewing my daily activity, I want to generate timelapse videos from screenshots, so that I can quickly review an entire day's work.

#### Acceptance Criteria

1. WHEN generating a timelapse, THE Timelapse_Generator SHALL create MP4 videos from daily screenshots using ffmpeg
2. WHEN ffmpeg is not available, THE Timelapse_Generator SHALL check for its presence using shutil.which and report an error if missing
3. WHEN creating timelapses, THE Timelapse_Generator SHALL support configurable frame rates with a default of 30 FPS
4. WHEN the OVERWRITE flag is true, THE Timelapse_Generator SHALL regenerate existing videos
5. WHEN the DELETE flag is true, THE Timelapse_Generator SHALL remove source screenshots after successful video encoding
6. THE Timelapse_Generator SHALL save generated videos in the same date directory as the source screenshots

### Requirement 6: Viewer Application

**User Story:** As a user reviewing my activity, I want a graphical interface to browse and view daily timelapses with focus information, so that I can analyze my productivity patterns.

#### Acceptance Criteria

1. WHEN browsing dates, THE Viewer_GUI SHALL display a calendar widget with visual indicators for available data
2. WHEN a date has screenshots, THE Viewer_GUI SHALL show a blue dot indicator on the calendar
3. WHEN a date has a generated timelapse video, THE Viewer_GUI SHALL show the date in green bold text
4. WHEN a date is selected, THE Viewer_GUI SHALL load and display the corresponding timelapse video if available
5. WHEN displaying focus data, THE Viewer_GUI SHALL show a timeline of window focus events synchronized with the video playback
6. THE Viewer_GUI SHALL communicate between components using PyQt signals for date selection, error handling, and loading states

### Requirement 7: Error Handling and Logging

**User Story:** As a system administrator, I want comprehensive error handling and logging, so that I can troubleshoot issues and monitor system health.

#### Acceptance Criteria

1. WHEN file I/O operations fail, THE Capture_Daemon SHALL wrap OSError and PermissionError with user-friendly messages
2. WHEN errors occur, THE Capture_Daemon SHALL store error messages in last_error_msg attributes for component access
3. WHEN logging events, THE Capture_Daemon SHALL write to daily rotating log files in ~/.logs/snap_span/
4. WHEN formatting log entries, THE Capture_Daemon SHALL use the format "YYYY-MM-DD HH:MM:SS - LEVEL - message"
5. THE Capture_Daemon SHALL provide both file and console log handlers for debugging

### Requirement 8: Data Format Validation

**User Story:** As a developer maintaining the system, I want strict data format validation, so that the system handles data consistently and prevents corruption.

#### Acceptance Criteria

1. WHEN parsing window_data.jsonl files, THE WindowDataParser SHALL process each line as a separate JSON object
2. WHEN encountering malformed JSONL, THE WindowDataParser SHALL report specific parsing errors with line numbers
3. WHEN validating directory structure, THE FileSystemReader SHALL verify the presence of required files in date directories
4. WHEN processing timestamps, THE WindowDataParser SHALL validate ISO format datetime strings
5. THE WindowDataParser SHALL NOT attempt to parse window_data.jsonl as a JSON array

### Requirement 9: Performance and Resource Management

**User Story:** As a user running the application continuously, I want efficient resource usage, so that the system doesn't impact my computer's performance.

#### Acceptance Criteria

1. WHEN capturing screenshots, THE Screenshot_Pipeline SHALL use the mss library for fast multi-platform screenshot capture
2. WHEN processing images, THE Screenshot_Pipeline SHALL use numpy arrays for efficient pixel difference calculations
3. WHEN scaling images, THE Screenshot_Pipeline SHALL use Pillow for optimized image manipulation
4. WHEN the change detection threshold is not met, THE Screenshot_Pipeline SHALL immediately discard the screenshot without saving
5. THE Capture_Daemon SHALL provide configurable capture intervals to balance monitoring detail with resource usage
