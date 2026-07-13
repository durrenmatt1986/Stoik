import json
import os
import subprocess
from pathlib import Path


DEFAULT_TIMEOUT = 180
SYSTEM_PYTHON = Path("/usr/bin/python3")
EXTERNAL_SENDER = Path(__file__).with_name("external_sender.py")


class TelegramError(RuntimeError):
    """Raised when Telegram returns an error or cannot be reached."""


def _parse_response(response_text):
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise TelegramError(
            "Telegram returned an unreadable response."
        ) from exc

    if not payload.get("ok"):
        description = payload.get(
            "description",
            "Unknown Telegram error",
        )
        error_code = payload.get("error_code")

        if error_code:
            raise TelegramError(
                f"Telegram API error {error_code}:\n"
                f"{description}"
            )

        raise TelegramError(description)

    return payload.get("result")


def _build_external_environment(bot_token):
    """Creates a clean environment for the standalone sender."""

    environment = os.environ.copy()

    for variable_name in (
        "LD_LIBRARY_PATH",
        "PYTHONHOME",
        "PYTHONPATH",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
    ):
        environment.pop(variable_name, None)

    environment["PATH"] = (
        "/usr/local/sbin:"
        "/usr/local/bin:"
        "/usr/sbin:"
        "/usr/bin:"
        "/sbin:"
        "/bin"
    )
    environment["STOIK_TELEGRAM_TOKEN"] = bot_token

    return environment


def call_method(
    bot_token,
    method,
    fields=None,
    files=None,
    timeout=DEFAULT_TIMEOUT,
    proxy="",
):
    """Calls Telegram through a standalone system-Python helper."""

    if not bot_token:
        raise TelegramError("Telegram bot token is empty.")

    if not SYSTEM_PYTHON.exists():
        raise TelegramError(
            "System Python was not found:\n"
            f"{SYSTEM_PYTHON}"
        )

    if not EXTERNAL_SENDER.exists():
        raise TelegramError(
            "External Telegram sender was not found:\n"
            f"{EXTERNAL_SENDER}"
        )

    fields = fields or {}
    files = files or {}
    serialised_files = {}

    for field_name, file_path in files.items():
        resolved_path = Path(file_path).expanduser().resolve()

        if not resolved_path.exists():
            raise TelegramError(
                "Telegram upload file was not found:\n"
                f"{resolved_path}"
            )

        if not resolved_path.is_file():
            raise TelegramError(
                "Telegram upload path is not a file:\n"
                f"{resolved_path}"
            )

        serialised_files[field_name] = str(resolved_path)

    command = [
        str(SYSTEM_PYTHON),
        str(EXTERNAL_SENDER),
        method,
        str(int(timeout)),
        json.dumps(fields, ensure_ascii=False),
        json.dumps(serialised_files, ensure_ascii=False),
        str(proxy or ""),
    ]

    environment = _build_external_environment(bot_token)

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=environment,
            timeout=timeout + 20,
            check=False,
            start_new_session=True,
        )
    except FileNotFoundError as exc:
        raise TelegramError(
            "Could not start the external Telegram sender."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise TelegramError(
            "Telegram upload timed out."
        ) from exc

    response_text = completed.stdout.strip()
    error_text = completed.stderr.strip()

    if response_text:
        return _parse_response(response_text)

    if completed.returncode != 0:
        raise TelegramError(
            error_text
            or (
                "External Telegram sender exited with code "
                f"{completed.returncode}."
            )
        )

    raise TelegramError("Telegram returned an empty response.")
