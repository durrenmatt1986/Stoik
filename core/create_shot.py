from pathlib import Path

from core.shot_structure import SHOT_STRUCTURE


def create_shot(project_root, episode, shot_name):
    shot_root = Path(project_root) / episode / shot_name

    if shot_root.exists():
        raise FileExistsError(
            f"Шот уже существует: {shot_root}"
        )

    for folder in SHOT_STRUCTURE:
        folder_path = shot_root / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"Создано: {folder_path}")

    return shot_root