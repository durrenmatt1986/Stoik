import nuke

from Stoik.core.review_output import install_review_controls
from Stoik.core.source_loader import auto_load_source
from Stoik.ui.create_shot_dialog import show_create_shot_dialog
from Stoik.ui.shot_browser import show_shot_browser
from Stoik.ui.ftp_commands import open_current_shot_ftp
from Stoik.ui.publish_dialog import publish_preview_to_telegram
from Stoik.ui.render_commands import render_hires, render_preview


# Автоматически добавляет Stoik-кнопку всем Write-нодам.
install_review_controls()

# Автоматически ищет сорс и заполняет SOURCE_READ
# при открытии Nuke-скрипта.
nuke.addOnScriptLoad(auto_load_source)


stoik_menu = nuke.menu("Nuke").addMenu("Stoik")

stoik_menu.addCommand(
    "Shot Browser...",
    show_create_shot_dialog,
)
stoik_menu.addCommand(
    "Shot Browser 2.0...",
    show_shot_browser,
)

stoik_menu.addSeparator()

stoik_menu.addCommand(
    "Open Current Shot in FileZilla",
    open_current_shot_ftp,
)

stoik_menu.addSeparator()

stoik_menu.addCommand(
    "Render Preview",
    render_preview,
)

stoik_menu.addCommand(
    "Render Hires",
    render_hires,
)

stoik_menu.addSeparator()

publish_menu = stoik_menu.addMenu("Publish")

publish_menu.addCommand(
    "Telegram Preview...",
    publish_preview_to_telegram,
)
