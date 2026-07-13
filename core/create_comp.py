import shutil
from pathlib import Path


def create_comp(
    project_root,
    shot_group,
    shot_name,
    template_path,
):
    """Копирует шаблон Nuke в Comp/Work выбранного шота."""

    project_root = Path(project_root)
    template_path = Path(template_path)

    shot_root = project_root / shot_group / shot_name
    work_folder = shot_root / "Comp" / "Work"

    if not shot_root.exists():
        raise FileNotFoundError(f"Папка шота не найдена:\n{shot_root}")

    if not work_folder.exists():
        raise FileNotFoundError(f"Папка Comp/Work не найдена:\n{work_folder}")

    if not template_path.exists():
        raise FileNotFoundError(f"Шаблон Nuke не найден:\n{template_path}")

    comp_name = f"{shot_name}_comp_v001.nk"
    comp_path = work_folder / comp_name

    if comp_path.exists():
        raise FileExistsError(f"Скрипт уже существует:\n{comp_path}")

    shutil.copy2(template_path, comp_path)
    return comp_path
