from pathlib import Path

import nuke

from ..utils.filezilla import open_filezilla
from ..utils.settings import get_projects, load_settings


def _find_current_shot_source(settings):
    script_path = Path(nuke.root().name())

    if nuke.root().name() == "Root" or not script_path.is_absolute():
        raise RuntimeError(
            "Сначала открой или сохрани Nuke-скрипт внутри папки шота."
        )

    resolved_script = script_path.resolve()

    for project_name, project in get_projects(settings).items():
        project_root = Path(project["root"]).resolve()

        try:
            relative_path = resolved_script.relative_to(project_root)
        except ValueError:
            continue

        parts = relative_path.parts
        if len(parts) < 3:
            continue

        shot_group = parts[0]
        shot_name = parts[1]
        source_path = project_root / shot_group / shot_name / "input" / "source"

        return project_name, shot_group, shot_name, source_path

    raise RuntimeError(
        "Текущий скрипт не находится внутри ни одного проекта Stoik."
    )


def open_current_shot_ftp():
    """Открывает FileZilla в input/source текущего Nuke-шота."""

    try:
        settings = load_settings()
        project_name, shot_group, shot_name, source_path = (
            _find_current_shot_source(settings)
        )

        open_filezilla(
            executable_path=settings["ftp_program"],
            local_path=source_path,
        )

        nuke.message(
            "FileZilla открыта для текущего шота.\n\n"
            f"Проект: {project_name}\n"
            f"Группа: {shot_group}\n"
            f"Шот: {shot_name}\n\n"
            f"{source_path}"
        )

    except (KeyError, FileNotFoundError, RuntimeError) as error:
        nuke.message(str(error))
    except Exception as error:
        nuke.message(f"Ошибка Stoik при открытии FileZilla:\n\n{error}")
