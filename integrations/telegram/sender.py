from pathlib import Path

from .client import call_method
from .settings import load_telegram_credentials


def send_preview(preview_path):
    """Sends a preview movie to the configured Telegram chat."""

    preview_path = Path(preview_path)

    if not preview_path.exists():
        raise FileNotFoundError(
            "Preview file was not found:\n"
            f"{preview_path}"
        )

    if not preview_path.is_file():
        raise RuntimeError(
            "Preview path is not a file:\n"
            f"{preview_path}"
        )

    credentials = load_telegram_credentials()

    return call_method(
        bot_token=credentials["bot_token"],
        method="sendVideo",
        fields={
            "chat_id": credentials["chat_id"],
            "supports_streaming": "true",
        },
        files={"video": preview_path},
        proxy=credentials.get("proxy", ""),
    )
