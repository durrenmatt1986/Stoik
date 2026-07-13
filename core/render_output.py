from pathlib import Path


def get_current_comp_info(script_path):
    """
    Определяет имя компа и корень шота
    по пути открытого Nuke-скрипта.

    Ожидаемая структура:

    SHOT_NAME/
        Comp/
            Work/
                SHOT_NAME_comp_v001.nk
    """

    script_path = Path(script_path)

    if not script_path.name or script_path.name == "Root":
        raise RuntimeError(
            "Текущий Nuke-скрипт ещё не сохранён."
        )

    if script_path.suffix.lower() != ".nk":
        raise RuntimeError(
            "Открытый файл не является Nuke-скриптом:\n"
            f"{script_path}"
        )

    work_folder = script_path.parent
    comp_folder = work_folder.parent

    if work_folder.name.lower() != "work":
        raise RuntimeError(
            "Скрипт должен находиться в папке Comp/Work.\n\n"
            f"Текущая папка:\n{work_folder}"
        )

    if comp_folder.name.lower() != "comp":
        raise RuntimeError(
            "Не удалось определить папку Comp.\n\n"
            f"Текущий путь:\n{script_path}"
        )

    shot_root = comp_folder.parent
    comp_name = script_path.stem

    return {
        "script_path": script_path,
        "shot_root": shot_root,
        "comp_name": comp_name,
    }


def build_preview_path(comp_info):
    """
    Создаёт путь Preview на основе имени открытого скрипта.

    Например:

    SHOT_comp_v001.nk
    превращается в:
    SHOT_comp_v001.mov
    """

    preview_folder = (
        comp_info["shot_root"]
        / "output"
        / "Preview"
    )

    preview_filename = (
        f"{comp_info['comp_name']}.mov"
    )

    return preview_folder / preview_filename


def build_hires_path(comp_info):
    """
    Создаёт отдельную папку для каждой версии Hires.

    Например:

    SHOT_comp_v001.nk

    превращается в:

    output/
        Hires/
            SHOT_comp_v001/
                SHOT_comp_v001.%04d.exr
    """

    comp_name = comp_info["comp_name"]

    hires_version_folder = (
        comp_info["shot_root"]
        / "output"
        / "Hires"
        / comp_name
    )

    hires_version_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    hires_filename = (
        f"{comp_name}.%04d.exr"
    )

    return hires_version_folder / hires_filename