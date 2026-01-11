# Product Requirements Document (PRD): Fix `make check` Errors

## Overview
The `make check` command currently fails with 33 linting errors detected by ruff. This PRD outlines the requirements to resolve these errors and ensure the codebase adheres to the project's coding standards.

## Objectives
- Eliminate all linting errors reported by ruff in `make check`
- Improve code quality, readability, and maintainability
- Ensure consistent coding style across the viewer module
- Enable `make check` to pass without errors

## Background
The `make check` target runs several code quality tools including ruff for linting. The current errors are primarily in the `src/activity_beacon/viewer/` directory and include issues with:
- Missing type annotations
- Naming conventions
- Code complexity
- Unused arguments
- Magic numbers
- Boolean positional arguments

## Requirements

### Functional Requirements
1. **Type Annotations**: Add missing type annotations for function arguments and variables as indicated by ANN001 errors.
2. **Naming Conventions**: Rename functions and imports to follow lowercase conventions (N802, N812).
3. **Code Complexity**: Refactor complex functions to reduce cyclomatic complexity below thresholds (C901).
4. **Unused Arguments**: Handle or remove unused method arguments (ARG002).
5. **Magic Numbers**: Replace magic numbers with named constants (PLR2004).
6. **Boolean Arguments**: Use keyword arguments for boolean values instead of positional (FBT003).
7. **Nested Blocks**: Reduce excessive nesting in control structures (PLR1702).
8. **Method Classification**: Convert instance methods to static/class methods where appropriate (PLR6301).
9. **Statement Count**: Break down large methods with too many statements (PLR0915).

### Non-Functional Requirements
- Maintain existing functionality
- Ensure backward compatibility
- Follow Python best practices
- Use appropriate typing hints

## Specific Error Fixes Required

### calendar_widget.py
- Add type annotation for `file_system_reader` parameter
- Rename `paintCell` to `paint_cell`
- Add type annotation for `rect` parameter
- Handle unused `year` and `month` arguments in `_on_page_changed`

### filesystem_reader.py
- Rename `Date` import to lowercase `date`
- Refactor `get_available_dates` to reduce complexity and nesting
- Replace magic numbers (4, 2) with constants

### main.py
- Refactor `on_date_selected` to reduce complexity
- Rename `resizeEvent` to `resize_event`
- Add type annotation for `event` parameter

### video_player.py
- Refactor `__init__` to reduce statement count
- Use keyword arguments for boolean signals
- Convert `_fmt_ms` to static method
- Add type annotation for `*args`
- Replace magic number 2 with constant
- Reduce nesting in error handling

### window_data_parser.py
- Reduce nesting in file reading
- Convert `parse_line` and `match_timestamp_to_video_position` to static methods

## Acceptance Criteria
- `make check` runs successfully with exit code 0
- No ruff errors reported
- All code changes maintain existing functionality
- Code passes type checking with basedpyright
- Pre-commit hooks pass

## Dependencies
- Python 3.8+
- ruff linter
- basedpyright type checker
- Existing project dependencies

## Timeline
- Phase 1: Fix critical type annotation and naming issues
- Phase 2: Refactor complex methods
- Phase 3: Address remaining style issues
- Testing: Verify all changes work correctly

## Risks
- Refactoring complex methods may introduce bugs
- Type annotation changes may reveal additional type issues
- Performance impact from method restructuring

## Success Metrics
- 0 linting errors in `make check`
- Code coverage maintained
- No regression in functionality
- Improved code maintainability scores
