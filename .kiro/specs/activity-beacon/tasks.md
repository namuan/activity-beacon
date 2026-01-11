# Implementation Plan: ActivityBeacon Screenshot Capture System

## Overview

This implementation plan focuses on building the core screenshot capture daemon with multi-monitor support, change detection, window tracking, and organized file storage. The tasks build incrementally from basic screenshot capture to the full-featured system.

## Tasks

- [ ] 1. Set up project structure and core interfaces
  - Create core module structure for screenshot pipeline, window tracking, and file storage
  - Define data classes for WindowDataEntry, FocusedAppData, and WindowInfo
  - Set up logging configuration with daily rotating files
  - Configure basic testing framework
  - _Requirements: 5.3, 5.4, 5.5_

- [ ] 2. Implement basic screenshot capture system
  - [ ] 2.1 Create ScreenshotCapture class using mss library
    - Implement monitor enumeration and individual monitor capture
    - Handle monitor detection and geometry calculation
    - _Requirements: 1.1, 7.1_

  - [ ] 2.2 Implement ImageProcessor for multi-monitor stitching
    - Create scaling logic to match highest resolution
    - Implement horizontal stitching with aspect ratio preservation
    - _Requirements: 1.2, 1.3, 7.3_

  - [ ] 2.3 Write unit tests for screenshot capture and image processing
    - Test multi-monitor stitching with known configurations
    - Test aspect ratio preservation during scaling
    - _Requirements: 1.2, 1.3_

- [ ] 3. Implement change detection system
  - [ ] 3.1 Create ChangeDetector class with numpy-based pixel analysis
    - Implement pixel difference calculation using numpy arrays
    - Add configurable threshold comparison (default: 10)
    - _Requirements: 1.4, 1.5, 1.6, 7.2_

  - [ ] 3.2 Write unit tests for change detection
    - Test threshold behavior with controlled image differences
    - Test identical images, completely different images, and boundary cases
    - _Requirements: 1.4, 1.5, 1.6_

- [ ] 4. Implement window tracking system
  - [ ] 4.1 Create FocusTracker using AppKit.NSWorkspace
    - Implement active application detection with PID tracking
    - Extract focused window name from active application
    - _Requirements: 2.1, 4.1_

  - [ ] 4.2 Create WindowEnumerator using Quartz.CGWindowListCopyWindowInfo
    - Enumerate all visible windows with complete metadata
    - Extract application names, window names, PIDs, and focus status
    - _Requirements: 2.2, 4.2_

  - [ ] 4.3 Write unit tests for window tracking
    - Test window data collection completeness
    - Test focus detection accuracy
    - _Requirements: 2.1, 2.2_

- [ ] 5. Implement file storage system
  - [ ] 5.1 Create DateDirectoryManager for organized file storage
    - Implement date-based directory creation with zero-padding
    - Generate proper screenshot filenames (YYYYMMDD_HHMMSS.png)
    - _Requirements: 3.1, 3.2, 3.4_

  - [ ] 5.2 Create JSONLWriter for window data storage
    - Implement newline-delimited JSON writing (not JSON array)
    - Add ISO timestamp formatting for all entries
    - _Requirements: 2.3, 2.4, 2.5, 3.3_

  - [ ] 5.3 Write unit tests for file storage
    - Test JSONL format compliance
    - Test file organization and naming
    - Test directory structure validation
    - _Requirements: 2.3, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 6. Checkpoint - Core functionality validation
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement system integration layer
  - [ ] 7.1 Create SystemStateMonitor for screen lock detection
    - Implement screen lock detection using Quartz.CGSessionCopyCurrentDictionary
    - Add automatic pause/resume logic for capture cycles
    - _Requirements: 4.3, 4.4_

  - [ ] 7.2 Create MenuBarController using PyQt6
    - Implement system tray icon with basic controls
    - Add configuration interface for capture intervals
    - _Requirements: 4.5, 7.5_

  - [ ] 7.3 Write unit tests for system integration
    - Test screen lock behavior
    - Test menu bar functionality
    - _Requirements: 4.3, 4.4, 4.5_

- [ ] 8. Implement error handling and logging
  - [ ] 8.1 Add comprehensive error handling with user-friendly messages
    - Wrap OSError and PermissionError with descriptive messages
    - Store error messages in last_error_msg attributes
    - _Requirements: 5.1, 5.2_

  - [ ] 8.2 Implement logging system with proper formatting
    - Set up daily rotating log files in ~/.logs/snap_span/
    - Ensure log format compliance: "YYYY-MM-DD HH:MM:SS - LEVEL - message"
    - _Requirements: 5.3, 5.4, 5.5_

  - [ ] 8.3 Write unit tests for error handling and logging
    - Test error message wrapping
    - Test log format compliance
    - Test log file rotation
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 9. Implement data validation and parsing
  - [ ] 9.1 Create WindowDataParser for JSONL file processing
    - Implement line-by-line JSON parsing (not array parsing)
    - Add malformed data error reporting with line numbers
    - _Requirements: 6.1, 6.2, 6.5_

  - [ ] 9.2 Create FileSystemReader for directory validation
    - Validate presence of required files in date directories
    - Check for proper directory structure and file naming
    - _Requirements: 6.3_

  - [ ] 9.3 Add timestamp validation for ISO format compliance
    - Validate ISO 8601 datetime format in window data
    - Reject malformed timestamps with descriptive errors
    - _Requirements: 6.4_

  - [ ] 9.4 Write unit tests for data validation
    - Test JSONL parsing with valid and invalid data
    - Test directory structure validation
    - Test timestamp format validation
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 10. Integration and main application wiring
  - [ ] 10.1 Create main CaptureController to coordinate all components
    - Wire together screenshot pipeline, window tracking, and file storage
    - Implement timer-based capture cycle with configurable intervals
    - Add system state monitoring integration
    - _Requirements: 1.1, 7.5_

  - [ ] 10.2 Create application entry point and configuration
    - Set up command-line interface and configuration file support
    - Initialize logging and error handling systems
    - Handle application lifecycle and graceful shutdown
    - _Requirements: 5.3, 5.4, 5.5_

  - [ ] 10.3 Write integration tests for complete capture cycle
    - Test end-to-end screenshot capture, processing, and storage
    - Verify window data collection and JSONL writing
    - Test error recovery and system state handling
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 3.1, 3.2, 3.3_

- [ ] 11. Final checkpoint and validation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Unit tests validate functionality with controlled test cases
- Integration tests verify end-to-end functionality
- Checkpoints ensure incremental validation and user feedback
