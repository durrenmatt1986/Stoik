import re
from pathlib import Path

import nuke


STOIK_TAB_KNOB = "stoik_output_tab"
LOAD_OUTPUT_KNOB = "stoik_load_rendered_output"
SOURCE_WRITE_KNOB = "stoik_source_write"
REVIEW_NODE_PREFIX = "REVIEW_"
_CALLBACKS_INSTALLED = False

MOVIE_EXTENSIONS = {
    ".mov",
    ".mp4",
    ".m4v",
    ".avi",
    ".mkv",
    ".webm",
}


def _normalise_path(path):
    """Возвращает путь в формате, удобном для Nuke."""

    return str(path).replace("\\", "/")


def _safe_node_name(value):
    """Преобразует произвольное имя в безопасное имя Nuke-ноды."""

    safe_name = re.sub(r"[^A-Za-z0-9_]+", "_", value)
    safe_name = safe_name.strip("_")

    return safe_name or "OUTPUT"


def _get_write_file_path(write_node):
    """Получает вычисленный путь из file knob выбранной Write-ноды."""

    if write_node is None or write_node.Class() != "Write":
        raise RuntimeError(
            "Команда должна быть вызвана из Write-ноды."
        )

    file_knob = write_node.knob("file")

    if file_knob is None:
        raise RuntimeError(
            f"У ноды {write_node.name()} отсутствует параметр file."
        )

    output_path = file_knob.evaluate().strip()

    if not output_path:
        raise RuntimeError(
            f"У ноды {write_node.name()} не указан путь рендера."
        )

    return _normalise_path(output_path)


def _path_exists(output_path):
    """
    Проверяет существование обычного файла или файловой секвенции.

    Для путей с %04d и #### проверяется кадр из диапазона проекта.
    """

    path = Path(output_path)

    if path.exists():
        return True

    first_frame = int(nuke.root()["first_frame"].value())

    if "%" in output_path:
        try:
            candidate = output_path % first_frame

            if Path(candidate).exists():
                return True

        except (TypeError, ValueError):
            pass

    hash_match = re.search(r"(#+)", output_path)

    if hash_match:
        padding = len(hash_match.group(1))
        frame_text = str(first_frame).zfill(padding)

        candidate = (
            output_path[:hash_match.start()]
            + frame_text
            + output_path[hash_match.end():]
        )

        if Path(candidate).exists():
            return True

    return False


def _is_movie_file(output_path):
    """Проверяет, является ли результат видеофайлом."""

    suffix = Path(output_path).suffix.lower()

    return suffix in MOVIE_EXTENSIONS


def _find_existing_review_node(write_node):
    """Ищет Read, ранее созданный для конкретной Write-ноды."""

    write_full_name = write_node.fullName()

    for node in nuke.allNodes("Read"):
        source_knob = node.knob(SOURCE_WRITE_KNOB)

        if (
            source_knob is not None
            and source_knob.value() == write_full_name
        ):
            return node

    return None


def _create_review_node(write_node):
    """Создаёт Read-ноду для проверки результата Write-ноды."""

    review_name = (
        REVIEW_NODE_PREFIX
        + _safe_node_name(write_node.name())
    )

    review_node = nuke.nodes.Read(
        name=review_name,
        xpos=write_node.xpos(),
        ypos=write_node.ypos() + 120,
    )

    source_knob = nuke.String_Knob(
        SOURCE_WRITE_KNOB,
        "Stoik source Write",
    )
    source_knob.setVisible(False)

    review_node.addKnob(source_knob)

    return review_node


def _set_sequence_frame_range(read_node):
    """
    Устанавливает диапазон секвенции по диапазону текущего Nuke-скрипта.

    Используется только для последовательностей изображений.
    Диапазон MOV и других видеофайлов не изменяется.
    """

    first_frame = int(nuke.root()["first_frame"].value())
    last_frame = int(nuke.root()["last_frame"].value())

    for knob_name, value in (
        ("first", first_frame),
        ("last", last_frame),
        ("origfirst", first_frame),
        ("origlast", last_frame),
    ):
        knob = read_node.knob(knob_name)

        if knob is not None:
            knob.setValue(value)


def _configure_review_frame_range(read_node, output_path):
    """
    Настраивает диапазон только для последовательностей изображений.

    MOV и другие видеофайлы сохраняют собственный диапазон кадров,
    обычно начинающийся с первого кадра.
    """

    if _is_movie_file(output_path):
        return

    _set_sequence_frame_range(read_node)


def _connect_to_viewer(read_node):
    """Подключает загруженный результат к активному Viewer."""

    viewer = nuke.activeViewer()

    if viewer is None:
        viewer_node = nuke.nodes.Viewer(
            xpos=read_node.xpos(),
            ypos=read_node.ypos() + 140,
        )
    else:
        viewer_node = viewer.node()

    viewer_node.setInput(0, read_node)


def load_rendered_output(write_node=None):
    """
    Загружает результат Write-ноды в Read и подключает его к Viewer.

    MOV и другие видеофайлы загружаются с их естественным диапазоном.
    При повторном вызове существующая review-нода обновляется.
    """

    try:
        if write_node is None:
            write_node = nuke.thisNode()

        output_path = _get_write_file_path(write_node)

        if not _path_exists(output_path):
            should_continue = nuke.ask(
                "Файл рендера пока не найден:\n\n"
                f"{output_path}\n\n"
                "Всё равно создать или обновить Read-ноду?"
            )

            if not should_continue:
                return None

        review_node = _find_existing_review_node(write_node)

        if review_node is None:
            review_node = _create_review_node(write_node)

        review_node["file"].fromUserText(output_path)

        review_node[SOURCE_WRITE_KNOB].setValue(
            write_node.fullName()
        )

        reload_knob = review_node.knob("reload")

        if reload_knob is not None:
            reload_knob.execute()

        _configure_review_frame_range(
            read_node=review_node,
            output_path=output_path,
        )

        _connect_to_viewer(review_node)

        review_node.setSelected(True)
        nuke.show(review_node)

        return review_node

    except Exception as error:
        nuke.message(
            "Не удалось загрузить результат рендера:\n\n"
            f"{error}"
        )

        return None


def add_review_controls(write_node):
    """Добавляет вкладку Stoik и кнопку проверки в одну Write-ноду."""

    if write_node is None or write_node.Class() != "Write":
        return

    if write_node.knob(LOAD_OUTPUT_KNOB) is not None:
        return

    if write_node.knob(STOIK_TAB_KNOB) is None:
        write_node.addKnob(
            nuke.Tab_Knob(
                STOIK_TAB_KNOB,
                "Stoik",
            )
        )

    load_button = nuke.PyScript_Knob(
        LOAD_OUTPUT_KNOB,
        "Load Rendered Output",
    )

    load_button.setTooltip(
        "Загрузить результат этой Write-ноды в Read "
        "и подключить его к Viewer."
    )

    load_button.setCommand(
        "from Stoik.core.review_output import load_rendered_output; "
        "load_rendered_output(nuke.thisNode())"
    )

    write_node.addKnob(load_button)


def add_review_controls_to_all_writes():
    """Добавляет Stoik-кнопку всем Write-нодам открытого скрипта."""

    for write_node in nuke.allNodes(
        "Write",
        recurseGroups=True,
    ):
        add_review_controls(write_node)


def _add_review_controls_to_created_write():
    """Добавляет Stoik-кнопку только что созданной Write-ноде."""

    add_review_controls(nuke.thisNode())


def install_review_controls():
    """
    Устанавливает кнопки Stoik на существующие и новые Write-ноды.

    Кнопки добавляются:
    - Write-нодам уже открытого скрипта;
    - Write-нодам при загрузке другого .nk;
    - новым Write-нодам, созданным вручную.
    """

    global _CALLBACKS_INSTALLED

    add_review_controls_to_all_writes()

    if _CALLBACKS_INSTALLED:
        return

    nuke.addOnScriptLoad(add_review_controls_to_all_writes)
    nuke.addOnUserCreate(
        _add_review_controls_to_created_write,
        nodeClass="Write",
    )

    _CALLBACKS_INSTALLED = True
