import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from .menu import get_main_menu_keyboard

from core.json_manager import storage_manager, MONITORS_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Supprime une surveillance par son ID.
    Usage: /remove_watch <ID_du_moniteur>
    """
    # Vérifier l'usage
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            r"用法: /remove\_watch <监控\_ID> (使用 /list\_watches 查看 ID)",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Valider l'ID
    try:
        target_id = int(context.args[0])
        safe_id = escape_markdown(str(target_id), version=2)
    except ValueError:
        await update.message.reply_text(
            "⛔ ID 必须是一个整数。",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Lire les moniteurs
    try:
        monitors = await storage_manager.read_data(MONITORS_FILE)
    except Exception as e:
        await update.message.reply_text(
            f"⛔ 无法读取监控数据: {escape_markdown(str(e), version=2)}",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    if not monitors:
        await update.message.reply_text(
            "⚠️ 当前没有注册的监控。",
            reply_markup=get_main_menu_keyboard()
        )
        return

    initial_count = len(monitors)

    # Filtrer le moniteur à supprimer
    new_monitors = [m for m in monitors if m.get('id') != target_id]

    # Vérifier si l'ID existe
    if len(new_monitors) == initial_count:
        await update.message.reply_text(
            rf"⚠️ 监控 ID `{safe_id}` 未找到。",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Sauvegarder la nouvelle liste
    await storage_manager.write_data(MONITORS_FILE, new_monitors)

    logger.info(f"Surveillance ID {target_id} supprimée par {update.effective_user.username}")

    # Message de succès
    await update.message.reply_text(
        rf"🗑️ 监控 ID **`{safe_id}`** 已从列表中移除。",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=get_main_menu_keyboard()
    )
