from pathlib import Path

import nuke

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtWidgets

from ..core.create_comp import create_comp
from ..core.create_shot import create_shot
from ..core.project_browser import (
    create_shot_group,
    get_available_shot_groups,
    import_existing_shot_groups,
    remove_shot_group_from_list,
    sync_shot_groups,
)
from ..utils.settings import get_project, get_projects, load_settings


_DIALOG = None


class ImportShotGroupsDialog(QtWidgets.QDialog):
    def __init__(self, group_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Shot Groups")
        self.setMinimumSize(420, 360)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        label = QtWidgets.QLabel(
            "Select the project folders that should be added as Shot Groups:"
        )
        label.setWordWrap(True)
        layout.addWidget(label)

        self.group_list = QtWidgets.QListWidget()
        self.group_list.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.group_list.addItems(group_names)
        layout.addWidget(self.group_list, 1)

        hint = QtWidgets.QLabel(
            "Use Ctrl or Shift to select several folders."
        )
        hint.setStyleSheet("color: #8a8a8a;")
        layout.addWidget(hint)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Cancel
            | QtWidgets.QDialogButtonBox.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.group_list.itemSelectionChanged.connect(
            self._update_ok_button
        )
        self._update_ok_button()

    def _update_ok_button(self):
        ok_button = self.findChild(
            QtWidgets.QPushButton,
            "",
        )
        button_box = self.findChild(QtWidgets.QDialogButtonBox)
        if button_box is not None:
            ok_button = button_box.button(QtWidgets.QDialogButtonBox.Ok)
        if ok_button is not None:
            ok_button.setEnabled(bool(self.selected_groups()))

    def selected_groups(self):
        return [item.text() for item in self.group_list.selectedItems()]


class CreateShotsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_settings()

        self.setWindowTitle("Stoik — Shot Browser")
        self.setMinimumWidth(650)
        self.resize(720, 500)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)

        self._build_ui()
        self._connect_signals()
        self._populate_projects()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        project_layout = QtWidgets.QHBoxLayout()
        project_label = QtWidgets.QLabel("Project:")
        project_label.setMinimumWidth(90)
        self.project_combo = QtWidgets.QComboBox()
        project_layout.addWidget(project_label)
        project_layout.addWidget(self.project_combo, 1)
        main_layout.addLayout(project_layout)

        group_layout = QtWidgets.QHBoxLayout()
        group_label = QtWidgets.QLabel("Shot Group:")
        group_label.setMinimumWidth(90)
        self.group_combo = QtWidgets.QComboBox()
        self.create_group_button = QtWidgets.QPushButton("Create Group")
        self.import_groups_button = QtWidgets.QPushButton("Import Existing")
        self.remove_group_button = QtWidgets.QPushButton("Remove from List")
        group_layout.addWidget(group_label)
        group_layout.addWidget(self.group_combo, 1)
        group_layout.addWidget(self.create_group_button)
        group_layout.addWidget(self.import_groups_button)
        group_layout.addWidget(self.remove_group_button)
        main_layout.addLayout(group_layout)

        self.project_path_label = QtWidgets.QLabel()
        self.project_path_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self.project_path_label.setStyleSheet("color: #8a8a8a;")
        main_layout.addWidget(self.project_path_label)

        shots_label = QtWidgets.QLabel("New shots — one name per line:")
        main_layout.addWidget(shots_label)

        self.shots_edit = QtWidgets.QPlainTextEdit()
        self.shots_edit.setPlaceholderText(
            "PLD_EP101_NDZD026_00420\n"
            "PLD_EP101_ABCD014_00130"
        )
        self.shots_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        main_layout.addWidget(self.shots_edit, 1)

        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setStyleSheet("color: #8a8a8a;")
        main_layout.addWidget(self.status_label)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addStretch(1)
        self.close_button = QtWidgets.QPushButton("Close")
        self.create_button = QtWidgets.QPushButton(
            "Create Shots + Comp Scripts"
        )
        self.create_button.setDefault(True)
        buttons_layout.addWidget(self.close_button)
        buttons_layout.addWidget(self.create_button)
        main_layout.addLayout(buttons_layout)

    def _connect_signals(self):
        self.project_combo.currentTextChanged.connect(
            self._on_project_changed
        )
        self.create_group_button.clicked.connect(self._create_group)
        self.import_groups_button.clicked.connect(self._import_groups)
        self.remove_group_button.clicked.connect(self._remove_group_from_list)
        self.create_button.clicked.connect(self._create_shots)
        self.close_button.clicked.connect(self.close)

        self.refresh_timer = QtCore.QTimer(self)
        self.refresh_timer.setInterval(1000)
        self.refresh_timer.timeout.connect(self._refresh_groups_silently)
        self.refresh_timer.start()

    def _populate_projects(self):
        projects = get_projects(self.settings)
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        self.project_combo.addItems(sorted(projects, key=str.casefold))

        default_project = self.settings.get("default_project")
        if default_project in projects:
            self.project_combo.setCurrentText(default_project)

        self.project_combo.blockSignals(False)
        self._on_project_changed(self.project_combo.currentText())

    def _on_project_changed(self, project_name):
        if not project_name:
            return

        project = get_project(self.settings, project_name)
        self.project_path_label.setText(project["root"])

        current_group = self.group_combo.currentText()
        groups, removed_groups = sync_shot_groups(
            self.settings,
            project_name,
        )

        self.group_combo.clear()
        self.group_combo.addItems(groups)

        if current_group in groups:
            self.group_combo.setCurrentText(current_group)

        has_groups = bool(groups)
        self.group_combo.setEnabled(has_groups)
        self.remove_group_button.setEnabled(has_groups)
        self.create_button.setEnabled(has_groups)
        if removed_groups:
            removed_text = ", ".join(removed_groups)
            self.status_label.setText(
                f"Removed missing groups: {removed_text}"
            )
        else:
            self.status_label.setText(
                "Ready"
                if has_groups
                else "Create or import a Shot Group first."
            )

    def _refresh_groups_silently(self):
        if not self.isVisible():
            return

        project_name = self.project_combo.currentText()
        if not project_name:
            return

        try:
            current_group = self.group_combo.currentText()
            groups, removed_groups = sync_shot_groups(
                self.settings,
                project_name,
            )

            visible_groups = [
                self.group_combo.itemText(index)
                for index in range(self.group_combo.count())
            ]

            if groups != visible_groups:
                self.group_combo.blockSignals(True)
                self.group_combo.clear()
                self.group_combo.addItems(groups)

                if current_group in groups:
                    self.group_combo.setCurrentText(current_group)

                self.group_combo.blockSignals(False)

            has_groups = bool(groups)
            self.group_combo.setEnabled(has_groups)
            self.remove_group_button.setEnabled(has_groups)
            self.create_button.setEnabled(has_groups)

            if removed_groups:
                self.status_label.setText(
                    "Removed missing groups: "
                    + ", ".join(removed_groups)
                )
        except Exception as error:
            self.refresh_timer.stop()
            self.status_label.setText(str(error))

    def _remove_group_from_list(self):
        project_name = self.project_combo.currentText()
        group_name = self.group_combo.currentText()

        if not project_name or not group_name:
            return

        answer = QtWidgets.QMessageBox.question(
            self,
            "Remove Shot Group",
            (
                f"Remove '{group_name}' from the Stoik list?\n\n"
                "The folder and all files on disk will remain unchanged."
            ),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Cancel,
        )

        if answer != QtWidgets.QMessageBox.Yes:
            return

        try:
            removed = remove_shot_group_from_list(
                self.settings,
                project_name,
                group_name,
            )

            self._on_project_changed(project_name)

            if removed:
                self.status_label.setText(
                    f"Removed from Stoik list: {group_name}"
                )
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Stoik", str(error))

    def _create_group(self):
        project_name = self.project_combo.currentText()
        group_name, accepted = QtWidgets.QInputDialog.getText(
            self,
            "Create Shot Group",
            "Group name:",
        )

        if not accepted:
            return

        try:
            group_path = create_shot_group(
                self.settings,
                project_name,
                group_name,
            )
            self._on_project_changed(project_name)
            self.group_combo.setCurrentText(group_path.name)
            self.status_label.setText(f"Created: {group_path}")
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Stoik", str(error))

    def _import_groups(self):
        project_name = self.project_combo.currentText()

        try:
            available_groups = get_available_shot_groups(
                self.settings,
                project_name,
            )

            if not available_groups:
                QtWidgets.QMessageBox.information(
                    self,
                    "Stoik",
                    "No unimported project folders found.",
                )
                return

            dialog = ImportShotGroupsDialog(available_groups, self)
            if dialog.exec() != QtWidgets.QDialog.Accepted:
                return

            selected_groups = dialog.selected_groups()
            imported = import_existing_shot_groups(
                self.settings,
                project_name,
                selected_groups,
            )
            self._on_project_changed(project_name)

            if imported:
                self.group_combo.setCurrentText(imported[0])
                message = "Imported groups:\n\n" + "\n".join(imported)
            else:
                message = "No groups were imported."

            QtWidgets.QMessageBox.information(self, "Stoik", message)
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Stoik", str(error))

    def _shot_names(self):
        names = []
        duplicates = set()

        for line in self.shots_edit.toPlainText().splitlines():
            shot_name = line.strip()
            if not shot_name:
                continue
            if shot_name in names:
                duplicates.add(shot_name)
                continue
            names.append(shot_name)

        if duplicates:
            duplicate_list = "\n".join(sorted(duplicates, key=str.casefold))
            raise ValueError(
                "Duplicate shot names in the list:\n\n" + duplicate_list
            )

        return names

    def _create_shots(self):
        project_name = self.project_combo.currentText()
        shot_group = self.group_combo.currentText()

        try:
            shot_names = self._shot_names()
            if not shot_names:
                raise ValueError("Add at least one shot name.")

            project = get_project(self.settings, project_name)
            project_root = Path(project["root"])
            template_path = Path(project["template_path"])

            created = []
            failed = []

            self.create_button.setEnabled(False)
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

            for index, shot_name in enumerate(shot_names, start=1):
                self.status_label.setText(
                    f"Creating {index}/{len(shot_names)}: {shot_name}"
                )
                QtWidgets.QApplication.processEvents()

                try:
                    shot_root = create_shot(
                        project_root=project_root,
                        shot_group=shot_group,
                        shot_name=shot_name,
                    )
                    comp_path = create_comp(
                        project_root=project_root,
                        shot_group=shot_group,
                        shot_name=shot_name,
                        template_path=template_path,
                    )
                    created.append((shot_root, comp_path))
                except Exception as error:
                    failed.append((shot_name, str(error)))

            self._show_result(created, failed)

            if created:
                failed_names = {name for name, _ in failed}
                remaining_lines = [
                    name for name in shot_names if name in failed_names
                ]
                self.shots_edit.setPlainText("\n".join(remaining_lines))

        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Stoik", str(error))
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
            self.create_button.setEnabled(bool(self.group_combo.count()))
            self.status_label.setText("Ready")

    def _show_result(self, created, failed):
        lines = []

        if created:
            lines.append(f"Created successfully: {len(created)}")
            lines.extend(f"  • {shot_root.name}" for shot_root, _ in created)

        if failed:
            if lines:
                lines.append("")
            lines.append(f"Failed: {len(failed)}")
            for shot_name, error in failed:
                lines.append(f"  • {shot_name}: {error}")

        message = "\n".join(lines) if lines else "Nothing was created."

        if failed:
            QtWidgets.QMessageBox.warning(self, "Stoik — Result", message)
        else:
            QtWidgets.QMessageBox.information(self, "Stoik — Result", message)


def show_create_shot_dialog():
    global _DIALOG

    if _DIALOG is None:
        _DIALOG = CreateShotsDialog()

    _DIALOG.show()
    _DIALOG.raise_()
    _DIALOG.activateWindow()
