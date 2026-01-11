from unittest.mock import MagicMock, patch

from activity_beacon.system_state.system_state_monitor import SystemStateMonitor


class TestSystemStateMonitor:
    def test_init(self) -> None:
        monitor = SystemStateMonitor()
        assert monitor._pause_callback is None
        assert monitor._resume_callback is None
        assert monitor._was_locked is False

    def test_set_callbacks(self) -> None:
        monitor = SystemStateMonitor()
        pause_func = MagicMock()
        resume_func = MagicMock()

        monitor.set_callbacks(pause_func, resume_func)

        assert monitor._pause_callback is pause_func
        assert monitor._resume_callback is resume_func

    def test_set_callbacks_none(self) -> None:
        monitor = SystemStateMonitor()
        monitor.set_callbacks(None, None)
        assert monitor._pause_callback is None
        assert monitor._resume_callback is None

    @patch("activity_beacon.system_state.system_state_monitor.Quartz")
    def test_is_screen_locked_true(self, mock_quartz: MagicMock) -> None:
        mock_quartz.CGSessionCopyCurrentDictionary.return_value = {
            "CGSSessionScreenIsLocked": 1
        }
        monitor = SystemStateMonitor()
        assert monitor.is_screen_locked() is True

    @patch("activity_beacon.system_state.system_state_monitor.Quartz")
    def test_is_screen_locked_false(self, mock_quartz: MagicMock) -> None:
        mock_quartz.CGSessionCopyCurrentDictionary.return_value = {
            "CGSSessionScreenIsLocked": 0
        }
        monitor = SystemStateMonitor()
        assert monitor.is_screen_locked() is False

    @patch("activity_beacon.system_state.system_state_monitor.Quartz")
    def test_is_screen_locked_missing_key(self, mock_quartz: MagicMock) -> None:
        mock_quartz.CGSessionCopyCurrentDictionary.return_value = {}
        monitor = SystemStateMonitor()
        assert monitor.is_screen_locked() is False

    @patch("activity_beacon.system_state.system_state_monitor.Quartz")
    def test_is_screen_locked_none(self, mock_quartz: MagicMock) -> None:
        mock_quartz.CGSessionCopyCurrentDictionary.return_value = None
        monitor = SystemStateMonitor()
        assert monitor.is_screen_locked() is False

    @patch("activity_beacon.system_state.system_state_monitor.Quartz")
    def test_is_screen_locked_exception(self, mock_quartz: MagicMock) -> None:
        mock_quartz.CGSessionCopyCurrentDictionary.side_effect = RuntimeError(
            "Session error"
        )
        monitor = SystemStateMonitor()
        assert monitor.is_screen_locked() is False

    def test_get_state_description_locked(self) -> None:
        monitor = SystemStateMonitor()
        with patch.object(monitor, "is_screen_locked", return_value=True):
            assert monitor.get_state_description() == "locked"

    def test_get_state_description_unlocked(self) -> None:
        monitor = SystemStateMonitor()
        with patch.object(monitor, "is_screen_locked", return_value=False):
            assert monitor.get_state_description() == "unlocked"

    @patch("activity_beacon.system_state.system_state_monitor.Quartz")
    def test_check_and_notify_triggers_pause(self, mock_quartz: MagicMock) -> None:
        mock_quartz.CGSessionCopyCurrentDictionary.return_value = {
            "CGSSessionScreenIsLocked": 1
        }
        pause_func = MagicMock()
        monitor = SystemStateMonitor()
        monitor.set_callbacks(pause_func=pause_func)

        result = monitor.check_and_notify()

        assert result is True
        pause_func.assert_called_once()
        assert monitor._was_locked is True

    @patch("activity_beacon.system_state.system_state_monitor.Quartz")
    def test_check_and_notify_triggers_resume(self, mock_quartz: MagicMock) -> None:
        mock_quartz.CGSessionCopyCurrentDictionary.return_value = {
            "CGSSessionScreenIsLocked": 0
        }
        monitor = SystemStateMonitor()
        monitor._was_locked = True
        resume_func = MagicMock()
        monitor.set_callbacks(resume_callback=resume_func)

        result = monitor.check_and_notify()

        assert result is False
        resume_func.assert_called_once()
        assert monitor._was_locked is False

    @patch("activity_beacon.system_state.system_state_monitor.Quartz")
    def test_check_and_notify_no_change(self, mock_quartz: MagicMock) -> None:
        mock_quartz.CGSessionCopyCurrentDictionary.return_value = {
            "CGSSessionScreenIsLocked": 0
        }
        pause_func = MagicMock()
        resume_func = MagicMock()
        monitor = SystemStateMonitor()
        monitor.set_callbacks(pause_func, resume_func)

        result = monitor.check_and_notify()

        assert result is False
        pause_func.assert_not_called()
        resume_func.assert_not_called()

    @patch("activity_beacon.system_state.system_state_monitor.Quartz")
    def test_check_and_notify_state_transition(self, mock_quartz: MagicMock) -> None:
        monitor = SystemStateMonitor()
        pause_func = MagicMock()
        resume_func = MagicMock()
        monitor.set_callbacks(pause_func, resume_func)

        # Transition to locked
        mock_quartz.CGSessionCopyCurrentDictionary.return_value = {
            "CGSSessionScreenIsLocked": 1
        }
        monitor.check_and_notify()
        assert pause_func.call_count == 1
        assert resume_func.call_count == 0

        # Stay locked
        monitor.check_and_notify()
        assert pause_func.call_count == 1
        assert resume_func.call_count == 0

        # Transition to unlocked
        mock_quartz.CGSessionCopyCurrentDictionary.return_value = {
            "CGSSessionScreenIsLocked": 0
        }
        monitor.check_and_notify()
        assert pause_func.call_count == 1
        assert resume_func.call_count == 1

        # Stay unlocked
        monitor.check_and_notify()
        assert pause_func.call_count == 1
        assert resume_func.call_count == 1

    def test_check_and_notify_no_callbacks(self) -> None:
        monitor = SystemStateMonitor()
        with patch.object(monitor, "is_screen_locked", return_value=True):
            result = monitor.check_and_notify()
            assert result is True
            assert monitor._was_locked is True

    def test_check_and_notify_only_pause_callback(self) -> None:
        monitor = SystemStateMonitor()
        pause_func = MagicMock()
        monitor.set_callbacks(pause_func=pause_func)

        with patch.object(monitor, "is_screen_locked", return_value=True):
            monitor.check_and_notify()
            pause_func.assert_called_once()

        with patch.object(monitor, "is_screen_locked", return_value=False):
            monitor._was_locked = True
            monitor.check_and_notify()
            # Resume callback not set, so shouldn't be called
            assert pause_func.call_count == 1

    def test_check_and_notify_only_resume_callback(self) -> None:
        monitor = SystemStateMonitor()
        resume_func = MagicMock()
        monitor.set_callbacks(resume_callback=resume_func)
        monitor._was_locked = True

        with patch.object(monitor, "is_screen_locked", return_value=False):
            monitor.check_and_notify()
            resume_func.assert_called_once()

        with patch.object(monitor, "is_screen_locked", return_value=True):
            monitor.check_and_notify()
            # Pause callback not set, so shouldn't be called
            assert resume_func.call_count == 1
