from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import nuke

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtWidgets

from Stoik.core.render_output import (
    build_preview_path,
    get_current_comp_info,
)
from Stoik.integrations.telegram.sender import send_preview
from Stoik.integrations.telegram.settings import (
    load_telegram_credentials,
)


_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="StoikTelegram",
)
_ACTIVE_PUBLISH = None


def _get_current_preview_path():
    script_path = nuke.root().name()
    comp_info = get_current_comp_info(script_path)
    return Path(build_preview_path(comp_info))


class TelegramPublishJob(QtCore.QObject):
    """Runs Telegram upload outside Nuke's main UI thread."""

    def __init__(self, preview_path, parent=None):
        super().__init__(parent)

        self.preview_path = Path(preview_path)
        self.future = None

        self.progress = QtWidgets.QProgressDialog(
            "Sending preview to Telegram…",
            "Hide",
            0,
            0,
            parent,
        )
        self.progress.setWindowTitle("Stoik — Telegram Publish")
        self.progress.setWindowModality(QtCore.Qt.NonModal)
        self.progress.setMinimumDuration(0)
        self.progress.setAutoClose(False)
        self.progress.setAutoReset(False)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(150)
        self.timer.timeout.connect(self._check_result)

    def start(self):
        self.future = _EXECUTOR.submit(
            send_preview,
            self.preview_path,
        )

        self.progress.show()
        self.timer.start()

    def _check_result(self):
        global _ACTIVE_PUBLISH

        if self.future is None or not self.future.done():
            return

        self.timer.stop()
        self.progress.close()

        try:
            self.future.result()
        except Exception as error:
            nuke.message(
                "Telegram publish failed:\n\n"
                f"{error}"
            )
        else:
            nuke.message(
                "Preview sent to Telegram successfully.\n\n"
                f"{self.preview_path.name}"
            )
        finally:
            _ACTIVE_PUBLISH = None
            self.deleteLater()


def publish_preview_to_telegram():
    """Confirms and sends the current comp preview to Telegram."""

    global _ACTIVE_PUBLISH

    try:
        if _ACTIVE_PUBLISH is not None:
            nuke.message(
                "A Telegram upload is already running."
            )
            return

        preview_path = _get_current_preview_path()
        credentials = load_telegram_credentials()

        if not preview_path.exists():
            raise FileNotFoundError(
                "Preview for the current comp version was not found:\n\n"
                f"{preview_path}\n\n"
                "Render Preview first."
            )

        should_send = nuke.ask(
            "Send this preview to Telegram?\n\n"
            f"File:\n{preview_path}\n\n"
            f"Chat ID:\n{credentials['chat_id']}"
        )

        if not should_send:
            return

        parent = QtWidgets.QApplication.activeWindow()
        _ACTIVE_PUBLISH = TelegramPublishJob(
            preview_path=preview_path,
            parent=parent,
        )
        _ACTIVE_PUBLISH.start()

    except Exception as error:
        nuke.message(
            "Telegram publish failed:\n\n"
            f"{error}"
        )
