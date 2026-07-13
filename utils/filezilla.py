import subprocess
from pathlib import Path


def open_filezilla(executable_path, local_path):
    """
    Запускает FileZilla и открывает указанную папку
    в левой локальной панели.
    """

    executable_path = Path(executable_path)
    local_path = Path(local_path)

    if not executable_path.exists():
        raise FileNotFoundError(
            f"FileZilla не найдена: {executable_path}"
        )

    if not local_path.exists():
        raise FileNotFoundError(
            f"Локальная папка не существует: {local_path}"
        )

    subprocess.Popen(
        [
            str(executable_path),
            f"--local={local_path}",
        ]
    )