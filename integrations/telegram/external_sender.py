#!/usr/bin/env python3
"""Standalone Telegram uploader used outside the Nuke Python process."""

import json
import os
import subprocess
import sys
from pathlib import Path


TELEGRAM_API_ROOT = "https://api.telegram.org"
SYSTEM_CURL = Path("/usr/bin/curl")


def _fail(message, exit_code=1):
    print(message, file=sys.stderr)
    raise SystemExit(exit_code)


def main():
    if len(sys.argv) != 6:
        _fail(
            "Usage: external_sender.py "
            "METHOD TIMEOUT FIELDS_JSON FILES_JSON PROXY"
        )

    method = sys.argv[1]

    try:
        timeout = int(sys.argv[2])
    except ValueError:
        _fail("Invalid Telegram timeout value.")

    try:
        fields = json.loads(sys.argv[3])
        files = json.loads(sys.argv[4])
    except json.JSONDecodeError as error:
        _fail(f"Invalid Telegram payload: {error}")

    proxy = sys.argv[5].strip()
    bot_token = os.environ.get("STOIK_TELEGRAM_TOKEN", "").strip()

    if not bot_token:
        _fail("Telegram bot token is empty.")

    if not SYSTEM_CURL.exists():
        _fail(f"System curl was not found: {SYSTEM_CURL}")

    url = f"{TELEGRAM_API_ROOT}/bot{bot_token}/{method}"

    command = [
        str(SYSTEM_CURL),
        "--silent",
        "--show-error",
        "--ipv4",
        "--connect-timeout",
        "15",
        "--max-time",
        str(timeout),
        "--request",
        "POST",
    ]

    if proxy:
        command.extend([
            "--proxy",
            proxy,
        ])

    for name, value in fields.items():
        command.extend([
            "--form",
            f"{name}={value}",
        ])

    for field_name, file_path in files.items():
        resolved_path = Path(file_path).expanduser().resolve()

        if not resolved_path.exists():
            _fail(
                "Telegram upload file was not found:\n"
                f"{resolved_path}"
            )

        if not resolved_path.is_file():
            _fail(
                "Telegram upload path is not a file:\n"
                f"{resolved_path}"
            )

        command.extend([
            "--form",
            f"{field_name}=@{resolved_path}",
        ])

    command.append(url)

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.stdout:
        sys.stdout.write(completed.stdout)

    if completed.stderr:
        sys.stderr.write(completed.stderr)

    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
