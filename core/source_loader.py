from pathlib import Path

import nuke

from .find_source_sequence import find_main_exr_sequence
from ..utils.settings import get_projects, load_settings


SOURCE_READ_NODE_NAME = "SOURCE_READ"


def _normalise_path(path):
    return Path(path).expanduser().resolve()


def _find_project_for_script(script_path, settings):
    """Возвращает проект Stoik, внутри которого находится Nuke-скрипт."""

    script_path = _normalise_path(script_path)

    for project_name, project in get_projects(settings).items():
        project_root_value = project.get("root")

        if not project_root_value:
            continue

        project_root = _normalise_path(project_root_value)

        try:
            relative_path = script_path.relative_to(project_root)
        except ValueError:
            continue

        return {
            "name": project_name,
            "root": project_root,
            "relative_path": relative_path,
        }

    return None


def _get_shot_root(script_path, project_root):
    """
    Определяет корень шота по расположению скрипта.

    Ожидаемая структура:
    Project / Shot Group / Shot / Comp / Work / script.nk
    """

    script_path = _normalise_path(script_path)
    project_root = _normalise_path(project_root)

    try:
        relative_path = script_path.relative_to(project_root)
    except ValueError:
        return None

    parts = relative_path.parts

    if len(parts) < 5:
        return None

    shot_group = parts[0]
    shot_name = parts[1]

    if parts[2].casefold() != "comp":
        return None

    if parts[3].casefold() != "work":
        return None

    return project_root / shot_group / shot_name


def _configure_source_read(read_node, source_sequence):
    """Заполняет SOURCE_READ найденной EXR-секвенцией."""

    source_file = source_sequence["file"].replace("\\", "/")
    first_frame = int(source_sequence["first"])
    last_frame = int(source_sequence["last"])

    read_node["file"].setValue(source_file)
    read_node["first"].setValue(first_frame)
    read_node["last"].setValue(last_frame)
    read_node["origfirst"].setValue(first_frame)
    read_node["origlast"].setValue(last_frame)

    root = nuke.root()
    root["first_frame"].setValue(first_frame)
    root["last_frame"].setValue(last_frame)

    if root.knob("lock_range") is not None:
        root["lock_range"].setValue(True)


def auto_load_source():
    """
    Автоматически подключает основной EXR-сорс при открытии скрипта Stoik.

    Если скрипт находится вне проекта Stoik, папка source пуста или в
    шаблоне отсутствует SOURCE_READ, функция молча завершает работу.
    """

    script_name = nuke.root().name()

    if not script_name or script_name == "Root":
        return

    script_path = Path(script_name)

    if script_path.suffix.lower() != ".nk":
        return

    try:
        settings = load_settings()
        project_info = _find_project_for_script(script_path, settings)

        if project_info is None:
            return

        shot_root = _get_shot_root(
            script_path=script_path,
            project_root=project_info["root"],
        )

        if shot_root is None:
            return

        source_root = shot_root / "input" / "source"

        if not source_root.exists():
            return

        source_sequence = find_main_exr_sequence(source_root)
        read_node = nuke.toNode(SOURCE_READ_NODE_NAME)

        if read_node is None or read_node.Class() != "Read":
            return

        current_file = read_node["file"].value().replace("\\", "/")
        source_file = source_sequence["file"].replace("\\", "/")
        first_frame = int(source_sequence["first"])
        last_frame = int(source_sequence["last"])

        already_configured = (
            current_file == source_file
            and int(read_node["first"].value()) == first_frame
            and int(read_node["last"].value()) == last_frame
        )

        if already_configured:
            return

        _configure_source_read(
            read_node=read_node,
            source_sequence=source_sequence,
        )

        nuke.scriptSave()

        print(
            "Stoik: SOURCE_READ updated: "
            f"{source_file} ({first_frame}-{last_frame})"
        )

    except FileNotFoundError:
        return
    except Exception as error:
        print(f"Stoik: source auto-load failed: {error}")