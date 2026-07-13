import json
from pathlib import Path


SETTINGS_FILE = Path(__file__).resolve().parent.parent / "settings.json"


def _migrate_legacy_settings(settings):
    """Возвращает настройки в новом формате проектов."""

    if "projects" in settings:
        return settings

    project_root = settings.get("project_root")
    template_path = settings.get("template_path")

    if not project_root or not template_path:
        return settings

    migrated = dict(settings)
    migrated.pop("project_root", None)
    migrated.pop("template_path", None)
    migrated["default_project"] = "Polden"
    migrated["projects"] = {
        "Polden": {
            "root": project_root,
            "template_path": template_path,
            "shot_groups": [],
        }
    }
    return migrated


def load_settings():
    """Загружает настройки Stoik из settings.json."""

    if not SETTINGS_FILE.exists():
        raise FileNotFoundError(
            f"Файл настроек не найден: {SETTINGS_FILE}"
        )

    with SETTINGS_FILE.open("r", encoding="utf-8") as settings_file:
        settings = json.load(settings_file)

    return _migrate_legacy_settings(settings)


def save_settings(settings):
    """Атомарно сохраняет настройки Stoik."""

    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = SETTINGS_FILE.with_suffix(".json.tmp")

    with temporary_file.open("w", encoding="utf-8") as settings_file:
        json.dump(settings, settings_file, ensure_ascii=False, indent=4)
        settings_file.write("\n")

    temporary_file.replace(SETTINGS_FILE)


def get_projects(settings):
    projects = settings.get("projects", {})
    if not isinstance(projects, dict) or not projects:
        raise KeyError("projects")
    return projects


def get_project(settings, project_name):
    projects = get_projects(settings)

    if project_name not in projects:
        raise KeyError(f"projects.{project_name}")

    project = projects[project_name]

    if not project.get("root"):
        raise KeyError(f"projects.{project_name}.root")

    if not project.get("template_path"):
        raise KeyError(f"projects.{project_name}.template_path")

    project.setdefault("shot_groups", [])
    return project
