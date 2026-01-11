# Quality Check Fixes for Integration Tests

## Status: Completed

## Summary
Fixed ruff linting errors in `tests/test_integration.py` that were causing `make check` to fail.

## Changes Made

### tests/test_integration.py

1. **Fixed ARG001 (Unused function argument)**: Renamed `tmp_path` to `_tmp_path` in `mock_date_directory_manager` fixture

2. **Fixed ARG002 (Unused method arguments)**: Prefixed unused parameters with underscores:
   - `temp_output_dir` → `_temp_output_dir` in `test_screenshot_storage_integration`
   - `sample_focused_app` → `_sample_focused_app` in `test_window_data_collection_integration`
   - `sample_windows` → `_sample_windows` in `test_window_data_collection_integration`
   - `sample_focused_app` → `_sample_focused_app` in `test_save_all_captures_mode`
   - `sample_windows` → `_sample_windows` in `test_save_all_captures_mode`
   - `mock_system_state_monitor` → `_mock_system_state_monitor` in `test_screen_unlock_resume`

3. **Fixed PLR0917 (Too many positional arguments)**: Added `# noqa: PLR0917` comment to `test_save_all_captures_mode` which intentionally takes many fixture dependencies

4. **Fixed F401 (Unused imports)**: Removed unused `patch` import and `JSONLWriter` import

## Quality Checks
- Ruff linting: Pass
- All 17 integration tests passing
- Pre-existing basedpyright type errors in viewer module are unrelated to this fix
