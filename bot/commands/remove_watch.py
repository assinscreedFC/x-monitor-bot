import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode  # <-- Pour le formatage
from telegram.helpers import escape_markdown  # <-- Pour l'échappement
from .menu import get_main_menu_keyboard  # <-- Import du clavier principal

from core.json_manager import storage_manager, MONITORS_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Supprime une surveillance par son ID.
    Usage: /remove_watch <ID_du_moniteur>
    """
    # 1. Vérifier l'usage (TRADUCTION)
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "用法: /remove\_watch <监控\_ID> (使用 /list\_watches 查看 ID)",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
        )
        return

    # 2. Valider l'ID
    try:
        target_id = int(context.args[0])
        safe_id = escape_markdown(str(target_id), version=2)
    except ValueError:
        # TRADUCTION DE L'ERREUR DE VALEUR
        await update.message.reply_text(
            "⛔ ID 必须是一个整数。",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
        )
        return

    # 3. Lire les moniteurs
    monitors = await storage_manager.read_data(MONITORS_FILE)
    initial_count = len(monitors)

    # 4. Trouver et filtrer le moniteur à supprimer
    # Nouvelle liste SANS l'ID ciblé
    new_monitors = [m for m in monitors if m.get('id') != target_id]

    # 5. Vérifier le résultat
    if len(new_monitors) == initial_count:
        # TRADUCTION DU MESSAGE NON TROUVÉ
        await update.message.reply_text(
            rf"⚠️ 监控 ID `{safe_id}` 未找到\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
        )
        return

    # 6. Sauvegarder la nouvelle liste
    await storage_manager.write_data(MONITORS_FILE, new_monitors)

    logger.info(f"Surveillance ID {target_id} supprimée par {update.effective_user.username}")

    # TRADUCTION DU MESSAGE DE SUCCÈS
    await update.message.reply_text(
        rf"🗑️ 监控 ID **`{safe_id}`** 已从列表中移除\.",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
    )