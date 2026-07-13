from pathlib import Path

from .shot_structure import SHOT_STRUCTURE


def _validate_name(name, label):
    cleaned_name = name.strip()

    if not cleaned_name:
        raise ValueError(f"Не указано название {label}.")

    if cleaned_name in {".", ".."}:
        raise ValueError(f"Недопустимое название {label}: {cleaned_name}")

    if "/" in cleaned_name or "\\" in cleaned_name:
        raise ValueError(
            f"Название {label} не должно содержать / или \\."
        )

    return cleaned_name


def create_shot(project_root, shot_group, shot_name):
    shot_group = _validate_name(shot_group, "Shot Group")
    shot_name = _validate_name(shot_name, "шота")
    shot_root = Path(project_root) / shot_group / shot_name

    if shot_root.exists():
        raise FileExistsError(f"Шот уже существует: {shot_root}")

    for folder in SHOT_STRUCTURE:
        folder_path = shot_root / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"Создано: {folder_path}")

    return shot_root
