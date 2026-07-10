from core.create_shot import create_shot


try:
    result = create_shot(
        "/media/hdd2/Work/Kemnits_studio/Polden",
        "Ep101",
        "PLD_EP101_NDZD026_00360",
    )

    print(f"Готово: {result}")

except FileExistsError as error:
    print(f"Ошибка: {error}")