"""PreferencesDialog - Configuration dialog for ActivityBeacon."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from activity_beacon.logging import get_logger

logger = get_logger("activity_beacon.daemon.preferences_dialog")


class PreferencesDialog(QDialog):
    """
    Preferences dialog for ActivityBeacon.

    Allows configuration of:
    - Output directory for captures
    - Capture interval
    - Debug mode
    """

    def __init__(self) -> None:
        """Initialize the preferences dialog."""
        super().__init__()
        self.setWindowTitle("ActivityBeacon Preferences")
        self.setModal(True)
        self.setMinimumWidth(500)

        # Load current settings
        self._settings = QSettings("ActivityBeacon", "ActivityBeacon")
        self._load_settings()

        # Create UI
        self._setup_ui()

        logger.debug("PreferencesDialog initialized")

    def _load_settings(self) -> None:
        """Load current settings from QSettings."""
        default_output = str(Path.home() / "Documents" / "ActivityBeacon" / "data")
        self._output_dir = self._settings.value(
            "capture/output_directory", default_output
        )
        self._interval = int(self._settings.value("capture/interval_seconds", 30))
        self._debug_mode = bool(
            self._settings.value("general/debug_mode", defaultValue=False)
        )

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout()

        # Capture settings group
        capture_group = QGroupBox("Capture Settings")
        capture_layout = QFormLayout()

        # Output directory
        output_layout = QVBoxLayout()
        self._output_edit = QLineEdit(str(self._output_dir))
        self._output_edit.setReadOnly(True)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_output_directory)  # type: ignore[reportUnknownMemberType]
        output_layout.addWidget(self._output_edit)
        output_layout.addWidget(browse_button)
        capture_layout.addRow("Output Directory:", output_layout)

        # Capture interval
        self._interval_spin = QSpinBox()
        self._interval_spin.setMinimum(5)
        self._interval_spin.setMaximum(3600)
        self._interval_spin.setSuffix(" seconds")
        self._interval_spin.setValue(self._interval)
        capture_layout.addRow("Capture Interval:", self._interval_spin)

        capture_group.setLayout(capture_layout)
        layout.addWidget(capture_group)

        # General settings group
        general_group = QGroupBox("General Settings")
        general_layout = QFormLayout()

        # Debug mode
        self._debug_checkbox = QCheckBox()
        self._debug_checkbox.setChecked(self._debug_mode)
        general_layout.addRow("Debug Mode:", self._debug_checkbox)

        # Settings file location (read-only, for information)
        settings_path = QLabel(self._settings.fileName())
        settings_path.setWordWrap(True)
        settings_path.setStyleSheet("color: gray; font-size: 10pt;")
        general_layout.addRow("Settings File:", settings_path)

        general_group.setLayout(general_layout)
        layout.addWidget(general_group)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_and_accept)  # type: ignore[reportUnknownMemberType]
        button_box.rejected.connect(self.reject)  # type: ignore[reportUnknownMemberType]
        layout.addWidget(button_box)

        self.setLayout(layout)

    def _browse_output_directory(self) -> None:
        """Open a directory browser to select output directory."""
        current_dir = self._output_edit.text()
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            current_dir,
            QFileDialog.Option.ShowDirsOnly,
        )

        if directory:
            self._output_edit.setText(directory)
            logger.debug("Output directory changed to: %s", directory)

    def _save_and_accept(self) -> None:
        """Save settings and close dialog."""
        # Save to QSettings
        self._settings.setValue("capture/output_directory", self._output_edit.text())
        self._settings.setValue("capture/interval_seconds", self._interval_spin.value())
        self._settings.setValue("general/debug_mode", self._debug_checkbox.isChecked())
        self._settings.sync()

        logger.info("Settings saved:")
        logger.info("  Output directory: %s", self._output_edit.text())
        logger.info("  Capture interval: %d seconds", self._interval_spin.value())
        logger.info("  Debug mode: %s", self._debug_checkbox.isChecked())

        self.accept()
