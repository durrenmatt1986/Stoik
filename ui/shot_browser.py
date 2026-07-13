from pathlib import Path

import nuke

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtWidgets

from ..core.create_shot import create_shot
from ..core.project_browser import (
    get_available_shot_groups,
    remove_shot_group_from_list,
    sync_shot_groups,
)
from ..utils.settings import get_project, get_projects, load_settings


_DIALOG = None


class ShotBrowserDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_settings()

        self.setWindowTitle("Stoik — Shot Browser 2.0")
        self.resize(900, 600)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)

        self._build_ui()
        self._connect_signals()
        self._populate_projects()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        header_layout = QtWidgets.QHBoxLayout()
        header_label = QtWidgets.QLabel("Project:")
        header_label.setMinimumWidth(80)
        self.project_combo = QtWidgets.QComboBox()
        header_layout.addWidget(header_label)
        header_layout.addWidget(self.project_combo, 1)
        main_layout.addLayout(header_layout)

        self.project_path_label = QtWidgets.QLabel()
        self.project_path_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self.project_path_label.setStyleSheet("color: #8a8a8a;")
        main_layout.addWidget(self.project_path_label)

        body_layout = QtWidgets.QHBoxLayout()
        body_layout.setSpacing(12)

        left_panel = QtWidgets.QFrame()
        left_panel.setFrameShape(QtWidgets.QFrame.StyledPanel)
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        left_title = QtWidgets.QLabel("Shot Groups")
        left_title.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(left_title)

        self.group_list = QtWidgets.QListWidget()
        left_layout.addWidget(self.group_list, 1)

        group_buttons_layout = QtWidgets.QHBoxLayout()
        self.remove_group_button = QtWidgets.QPushButton("Remove from list")
        self.refresh_groups_button = QtWidgets.QPushButton("Refresh")
        group_buttons_layout.addWidget(self.refresh_groups_button)
        group_buttons_layout.addWidget(self.remove_group_button)
        left_layout.addLayout(group_buttons_layout)

        body_layout.addWidget(left_panel, 1)

        right_panel = QtWidgets.QFrame()
        right_panel.setFrameShape(QtWidgets.QFrame.StyledPanel)
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)

        right_title = QtWidgets.QLabel("Shots")
        right_title.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(right_title)

        self.shot_list = QtWidgets.QListWidget()
        right_layout.addWidget(self.shot_list, 1)

        shot_buttons_layout = QtWidgets.QHBoxLayout()
        self.create_shot_button = QtWidgets.QPushButton("Create Shot")
        self.open_folder_button = QtWidgets.QPushButton("Open Group Folder")
        shot_buttons_layout.addWidget(self.open_folder_button)
        shot_buttons_layout.addWidget(self.create_shot_button)
        right_layout.addLayout(shot_buttons_layout)

        body_layout.addWidget(right_panel, 2)
        main_layout.addLayout(body_layout)

        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setStyleSheet("color: #8a8a8a;")
        main_layout.addWidget(self.status_label)

    def _connect_signals(self):
        self.project_combo.currentTextChanged.connect(self._on_project_changed)
        self.group_list.currentItemChanged.connect(self._on_group_changed)
        self.refresh_groups_button.clicked.connect(self._refresh_groups)
        self.remove_group_button.clicked.connect(self._remove_group)
        self.create_shot_button.clicked.connect(self._create_shot)
        self.open_folder_button.clicked.connect(self._open_group_folder)

    def _populate_projects(self):
        projects = get_projects(self.settings)
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        self.project_combo.addItems(sorted(projects, key=str.casefold))
        self.project_combo.blockSignals(False)

        default_project = self.settings.get("default_project")
        if default_project in projects:
            self.project_combo.setCurrentText(default_project)

        if not self.project_combo.currentText() and self.project_combo.count() > 0:
            self.project_combo.setCurrentIndex(0)

        self._on_project_changed(self.project_combo.currentText())

    def _on_project_changed(self, project_name):
        if not project_name:
            self.status_label.setText("No project selected.")
            self.project_path_label.setText("")
            self.group_list.clear()
            self.shot_list.clear()
            return

        project = get_project(self.settings, project_name)
        self.project_path_label.setText(project["root"])

        groups, removed_groups = sync_shot_groups(
            self.settings,
            project_name,
        )

        self.group_list.clear()
        self.group_list.addItems(groups)

        self.shot_list.clear()

        if removed_groups:
            self.status_label.setText(
                "Removed missing groups: " + ", ".join(removed_groups)
            )
        else:
            self.status_label.setText("Ready")

        if groups:
            self.group_list.setCurrentRow(0)
        else:
            self.status_label.setText("No shot groups available.")

    def _on_group_changed(self, current, previous=None):
        if current is None:
            self.shot_list.clear()
            return

        self._load_shots(current.text())

    def _refresh_groups(self):
        project_name = self.project_combo.currentText()
        if not project_name:
            return
        self._on_project_changed(project_name)

    def _remove_group(self):
        project_name = self.project_combo.currentText()
        group_name = self.group_list.currentItem()
        if not project_name or group_name is None:
            return

        answer = QtWidgets.QMessageBox.question(
            self,
            "Stoik",
            (
                f"Remove '{group_name.text()}' from the Stoik list?\n\n"
                "This will not delete the folder on disk."
            ),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Cancel,
        )

        if answer != QtWidgets.QMessageBox.Yes:
            return

        removed = remove_shot_group_from_list(
            self.settings,
            project_name,
            group_name.text(),
        )

        if removed:
            self.status_label.setText(
                f"Removed from Stoik list: {group_name.text()}"
            )
            self._refresh_groups()

    def _create_shot(self):
        project_name = self.project_combo.currentText()
        group_name = self.group_list.currentItem()

        if not project_name:
            QtWidgets.QMessageBox.warning(
                self,
                "Stoik",
                "Select a project first.",
            )
            return

        if group_name is None:
            QtWidgets.QMessageBox.warning(
                self,
                "Stoik",
                "Select a shot group first.",
            )
            return

        shot_name, accepted = QtWidgets.QInputDialog.getText(
            self,
            "Create Shot",
            "Shot name:",
        )

        if not accepted or not shot_name.strip():
            return

        project = get_project(self.settings, project_name)
        project_root = Path(project["root"])

        try:
            shot_root = create_shot(
                project_root=project_root,
                shot_group=group_name.text(),
                shot_name=shot_name,
            )
            self.status_label.setText(f"Created shot: {shot_root}")
            self._load_shots(group_name.text())
        except Exception as error:
            QtWidgets.QMessageBox.critical(
                self,
                "Stoik",
                str(error),
            )

    def closeEvent(self, event):
        global _DIALOG
        _DIALOG = None
        super().closeEvent(event)

    def _open_group_folder(self):
        group_name = self.group_list.currentItem()
        project_name = self.project_combo.currentText()

        if group_name is None or not project_name:
            return

        project = get_project(self.settings, project_name)
        group_path = Path(project["root"]) / group_name.text()

        if group_path.exists():
            nuke.openDirectory(str(group_path))
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "Stoik",
                "Group folder does not exist on disk.",
            )

    def _load_shots(self, group_name):
        self.shot_list.clear()

        project_name = self.project_combo.currentText()
        if not project_name or not group_name:
            return

        project = get_project(self.settings, project_name)
        group_path = Path(project["root"]) / group_name

        if not group_path.exists():
            self.status_label.setText(
                f"Group folder missing on disk: {group_path}"
            )
            return

        shots = sorted(
            [
                path.name
                for path in group_path.iterdir()
                if path.is_dir() and not path.name.startswith('.')
            ],
            key=str.casefold,
        )

        self.shot_list.addItems(shots)

        if not shots:
            self.status_label.setText("No shots found in this group.")
        else:
            self.status_label.setText("Ready")


def show_shot_browser():
    global _DIALOG

    if _DIALOG is not None:
        _DIALOG.activateWindow()
        _DIALOG.raise_()
        return

    parent = QtWidgets.QApplication.activeWindow()
    _DIALOG = ShotBrowserDialog(parent=parent)
    _DIALOG.show()
