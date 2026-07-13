from pathlib import Path

from ..utils.settings import get_project, save_settings


def _validate_folder_name(name, label):
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


def _existing_project_folders(project_root):
    if not project_root.exists():
        raise FileNotFoundError(
            f"Корневая папка проекта не найдена:\n{project_root}"
        )

    return sorted(
        (
            path.name
            for path in project_root.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        ),
        key=str.casefold,
    )


def create_shot_group(settings, project_name, group_name):
    """Создаёт папку группы и сохраняет её в настройках проекта."""

    group_name = _validate_folder_name(group_name, "группы")
    project = get_project(settings, project_name)
    project_root = Path(project["root"])
    group_path = project_root / group_name

    group_path.mkdir(parents=True, exist_ok=True)

    groups = project.setdefault("shot_groups", [])
    if group_name not in groups:
        groups.append(group_name)
        groups.sort(key=str.casefold)
        save_settings(settings)

    return group_path


def sync_shot_groups(settings, project_name):
    """Удаляет из настроек группы, папок которых больше нет на диске."""

    project = get_project(settings, project_name)
    project_root = Path(project["root"])
    existing_folders = set(_existing_project_folders(project_root))

    groups = project.setdefault("shot_groups", [])
    synced_groups = [name for name in groups if name in existing_folders]
    synced_groups.sort(key=str.casefold)

    removed = sorted(
        set(groups) - set(synced_groups),
        key=str.casefold,
    )

    if synced_groups != groups:
        project["shot_groups"] = synced_groups
        save_settings(settings)

    return synced_groups, removed


def get_available_shot_groups(settings, project_name):
    """Возвращает папки проекта, которые ещё не импортированы как группы."""

    project = get_project(settings, project_name)
    project_root = Path(project["root"])
    existing_folders = _existing_project_folders(project_root)
    registered_groups = set(project.setdefault("shot_groups", []))

    return [
        folder_name
        for folder_name in existing_folders
        if folder_name not in registered_groups
    ]


def import_existing_shot_groups(settings, project_name, group_names):
    """Импортирует только выбранные существующие папки как Shot Groups."""

    project = get_project(settings, project_name)
    project_root = Path(project["root"])
    existing_folders = set(_existing_project_folders(project_root))

    validated_names = []
    for group_name in group_names:
        cleaned_name = _validate_folder_name(group_name, "группы")
        if cleaned_name not in existing_folders:
            raise FileNotFoundError(
                "Папка Shot Group больше не существует:\n"
                f"{project_root / cleaned_name}"
            )
        if cleaned_name not in validated_names:
            validated_names.append(cleaned_name)

    groups = project.setdefault("shot_groups", [])
    imported = []

    for group_name in validated_names:
        if group_name not in groups:
            groups.append(group_name)
            imported.append(group_name)

    groups.sort(key=str.casefold)

    if imported:
        save_settings(settings)

    return imported


def remove_shot_group_from_list(settings, project_name, group_name):
    """Удаляет Shot Group только из настроек, не трогая папку на диске."""

    group_name = _validate_folder_name(group_name, "группы")
    project = get_project(settings, project_name)
    groups = project.setdefault("shot_groups", [])

    if group_name not in groups:
        return False

    project["shot_groups"] = [
        name for name in groups if name != group_name
    ]
    save_settings(settings)
    return True
