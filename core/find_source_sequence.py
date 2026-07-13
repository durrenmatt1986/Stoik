import re
from collections import defaultdict
from pathlib import Path


FRAME_PATTERN = re.compile(
    r"^(.*?)(\d+)(\.exr)$",
    re.IGNORECASE,
)


def find_exr_sequences(source_root):
    """
    Рекурсивно находит EXR-секвенции внутри source_root.

    Возвращает список словарей с данными каждой найденной
    последовательности.
    """

    source_root = Path(source_root)

    if not source_root.exists():
        raise FileNotFoundError(
            f"Папка с исходниками не найдена:\n{source_root}"
        )

    sequences = defaultdict(list)

    for file_path in source_root.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() != ".exr":
            continue

        match = FRAME_PATTERN.match(file_path.name)

        if not match:
            continue

        prefix = match.group(1)
        frame_text = match.group(2)
        suffix = match.group(3)

        padding = len(frame_text)
        frame_number = int(frame_text)

        sequence_key = (
            file_path.parent,
            prefix,
            padding,
            suffix.lower(),
        )

        sequences[sequence_key].append(frame_number)

    result = []

    for sequence_key, frames in sequences.items():
        parent, prefix, padding, suffix = sequence_key

        frames = sorted(set(frames))

        nuke_pattern = (
            parent
            / f"{prefix}%0{padding}d{suffix}"
        )

        result.append(
            {
                "file": str(nuke_pattern),
                "first": frames[0],
                "last": frames[-1],
                "frame_count": len(frames),
                "padding": padding,
            }
        )

    return result


def find_main_exr_sequence(source_root):
    """
    Возвращает самую крупную EXR-секвенцию.

    Если секвенций несколько, основной считается та,
    в которой найдено больше всего кадров.
    """

    sequences = find_exr_sequences(source_root)

    if not sequences:
        raise FileNotFoundError(
            "В папке исходников не найдено ни одной "
            f"EXR-секвенции:\n{source_root}"
        )

    return max(
        sequences,
        key=lambda sequence: sequence["frame_count"],
    )