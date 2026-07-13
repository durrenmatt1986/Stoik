import json
from pathlib import Path


CREDENTIALS_PATH = (
    Path(__file__).resolve().parents[2]
    / "telegram_credentials.json"
)


class TelegramSettingsError(RuntimeError):
    """Raised when Telegram credentials are missing or invalid."""


def load_telegram_credentials():
    """Loads the local bot token, chat ID and optional proxy."""

    if not CREDENTIALS_PATH.exists():
        raise TelegramSettingsError(
            "telegram_credentials.json was not found:\n"
            f"{CREDENTIALS_PATH}"
        )

    try:
        with CREDENTIALS_PATH.open("r", encoding="utf-8") as file_handle:
            credentials = json.load(file_handle)
    except json.JSONDecodeError as exc:
        raise TelegramSettingsError(
            "telegram_credentials.json contains invalid JSON."
        ) from exc

    bot_token = str(credentials.get("bot_token", "")).strip()
    chat_id = str(credentials.get("chat_id", "")).strip()
    proxy = str(credentials.get("proxy", "")).strip()

    if not bot_token:
        raise TelegramSettingsError(
            "Add bot_token to telegram_credentials.json."
        )

    if not chat_id:
        raise TelegramSettingsError(
            "Add chat_id to telegram_credentials.json."
        )

    return {
        "bot_token": bot_token,
        "chat_id": chat_id,
        "proxy": proxy,
    }
