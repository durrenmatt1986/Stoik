v0.0.3

Добавили нопку во все Write Ноды чтобы он подгружал то что отсчитано. В связи с этим добавлен новый файл с кодом review_output.py.Убрали старую функцию create comp, так как он был тестовый.
v0.0.4

Добавлен отдельный рендер Hires через WRITE_HIRES. Hires сохраняется EXR-секвенцией в output/Hires с именем текущей версии компа. Colorspace: ACES - ACES2065-1. В меню Stoik добавлена команда Render Hires.

v0.0.5

Добавлена первая минимальная интеграция Telegram Publish. В меню Stoik появился пункт Publish → Telegram Preview. Команда находит preview текущей версии компа, показывает подтверждение и отправляет MOV без подписи в chat_id из локального telegram_credentials.json.

## Telegram proxy fix

Telegram Publish now supports an explicit proxy from `telegram_credentials.json`.
The external sender calls the system curl directly and no longer starts an interactive bash shell.
This allows publishing from NukeX launched through the desktop icon when the workstation routes Telegram through a local proxy.
