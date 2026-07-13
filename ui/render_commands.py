from pathlib import Path

import nuke

from ..core.render_output import (
    build_hires_path,
    build_preview_path,
    get_current_comp_info,
)
from ..utils.settings import load_settings


PREVIEW_WRITE_NODE_NAME = "WRITE_PREVIEW"
HIRES_WRITE_NODE_NAME = "WRITE_HIRES"


def get_write_node(node_name):
    """Находит Write-ноду по имени и проверяет её тип."""

    write_node = nuke.toNode(node_name)

    if write_node is None:
        raise RuntimeError(
            "В скрипте не найдена Write-нода:\n"
            f"{node_name}"
        )

    if write_node.Class() != "Write":
        raise RuntimeError(
            f"Нода {node_name} существует, но это не Write."
        )

    return write_node


def set_enum_knob_value(
    node,
    knob_names,
    preferred_values,
    description,
):
    """
    Находит подходящий knob и устанавливает
    одно из допустимых значений.
    """

    for knob_name in knob_names:
        knob = node.knob(knob_name)

        if knob is None:
            continue

        try:
            available_values = list(knob.values())
        except Exception:
            available_values = []

        if available_values:
            for preferred_value in preferred_values:
                for available_value in available_values:
                    if (
                        available_value.strip().lower()
                        == preferred_value.strip().lower()
                    ):
                        knob.setValue(available_value)
                        return knob_name

        for preferred_value in preferred_values:
            try:
                knob.setValue(preferred_value)
                return knob_name
            except Exception:
                continue

    raise RuntimeError(
        f"Не удалось настроить {description}.\n\n"
        "Проверенные параметры:\n"
        + "\n".join(knob_names)
    )


def set_colorspace(write_node, colorspace):
    """Устанавливает colorspace с учётом разных версий Nuke."""

    for knob_name in ("colorspace", "ocioColorspace"):
        knob = write_node.knob(knob_name)

        if knob is None:
            continue

        try:
            knob.setValue(colorspace)
            return
        except Exception:
            try:
                available_values = list(knob.values())
            except Exception:
                available_values = []

            for available_value in available_values:
                if (
                    available_value.strip().lower()
                    == colorspace.strip().lower()
                ):
                    knob.setValue(available_value)
                    return

    raise RuntimeError(
        "Не удалось установить цветовое пространство:\n"
        f"{colorspace}"
    )


def configure_preview_write(
    write_node,
    preview_path,
    preview_settings,
):
    """Настраивает WRITE_PREVIEW для MOV/H.264."""

    preview_path = Path(preview_path)
    preview_path.parent.mkdir(parents=True, exist_ok=True)

    nuke_path = str(preview_path).replace("\\", "/")

    write_node["file"].setValue(nuke_path)
    write_node["file_type"].setValue(
        preview_settings["file_type"]
    )

    nuke.executeInMainThread(lambda: None)

    set_enum_knob_value(
        node=write_node,
        knob_names=[
            "mov64_codec",
            "mov_codec",
            "codec",
        ],
        preferred_values=[
            preview_settings["codec"],
            "H.264",
            "h264",
            "H264",
        ],
        description="кодек H.264",
    )

    set_colorspace(
        write_node,
        preview_settings["colorspace"],
    )

    return preview_path


def configure_hires_write(
    write_node,
    hires_path,
    hires_settings,
):
    """Настраивает WRITE_HIRES для EXR в ACES2065-1."""

    hires_path = Path(hires_path)
    hires_path.parent.mkdir(parents=True, exist_ok=True)

    nuke_path = str(hires_path).replace("\\", "/")

    write_node["file"].setValue(nuke_path)
    write_node["file_type"].setValue(
        hires_settings["file_type"]
    )

    nuke.executeInMainThread(lambda: None)

    set_colorspace(
        write_node,
        hires_settings["colorspace"],
    )

    return hires_path


def get_render_range():
    """Возвращает текущий диапазон проекта."""

    root = nuke.root()

    first_frame = int(root["first_frame"].value())
    last_frame = int(root["last_frame"].value())

    if last_frame < first_frame:
        raise RuntimeError(
            "Некорректный диапазон кадров:\n"
            f"{first_frame}–{last_frame}"
        )

    return first_frame, last_frame


def render_preview():
    """Настраивает WRITE_PREVIEW и запускает MOV/H.264."""

    try:
        comp_info = get_current_comp_info(
            nuke.root().name()
        )
        preview_path = build_preview_path(comp_info)

        settings = load_settings()
        preview_settings = settings["preview"]

        write_node = get_write_node(
            PREVIEW_WRITE_NODE_NAME
        )

        configure_preview_write(
            write_node=write_node,
            preview_path=preview_path,
            preview_settings=preview_settings,
        )

        first_frame, last_frame = get_render_range()
        nuke.scriptSave()

        should_render = nuke.ask(
            "Запустить рендер Preview?\n\n"
            f"Кадры: {first_frame}–{last_frame}\n"
            "Формат: MOV\n"
            "Кодек: H.264\n"
            f"Colorspace: {preview_settings['colorspace']}\n\n"
            f"Файл:\n{preview_path}"
        )

        if not should_render:
            return

        nuke.execute(write_node, first_frame, last_frame)

        nuke.message(
            "Preview успешно просчитано:\n\n"
            f"{preview_path}"
        )

    except KeyError as error:
        nuke.message(
            "В settings.json отсутствует настройка:\n\n"
            f"{error}"
        )
    except Exception as error:
        nuke.message(
            "Ошибка Stoik при рендере Preview:\n\n"
            f"{error}"
        )


def render_hires():
    """Настраивает WRITE_HIRES и запускает EXR в ACES2065-1."""

    try:
        comp_info = get_current_comp_info(
            nuke.root().name()
        )
        hires_path = build_hires_path(comp_info)

        settings = load_settings()
        hires_settings = settings["hires"]

        write_node = get_write_node(
            HIRES_WRITE_NODE_NAME
        )

        configure_hires_write(
            write_node=write_node,
            hires_path=hires_path,
            hires_settings=hires_settings,
        )

        first_frame, last_frame = get_render_range()
        nuke.scriptSave()

        should_render = nuke.ask(
            "Запустить рендер Hires?\n\n"
            f"Кадры: {first_frame}–{last_frame}\n"
            "Формат: EXR sequence\n"
            f"Colorspace: {hires_settings['colorspace']}\n\n"
            f"Файл:\n{hires_path}"
        )

        if not should_render:
            return

        nuke.execute(write_node, first_frame, last_frame)

        nuke.message(
            "Hires успешно просчитан:\n\n"
            f"{hires_path}"
        )

    except KeyError as error:
        nuke.message(
            "В settings.json отсутствует настройка:\n\n"
            f"{error}"
        )
    except Exception as error:
        nuke.message(
            "Ошибка Stoik при рендере Hires:\n\n"
            f"{error}"
        )
