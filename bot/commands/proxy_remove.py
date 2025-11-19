import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from .menu import get_main_menu_keyboard

from core.json_manager import storage_manager, PROXIES_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Supprime un proxy par son ID.
    Usage: /proxy_remove <ID_du_proxy>
    """

    # 1. Vérification de l'usage
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            r"用法: /proxy\_remove <代理\_ID> （使用 /proxy\_list 查看所有 ID）",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    # 2. Validation de l'ID
    try:
        target_id = int(context.args[0])
        safe_id = escape_markdown(str(target_id), version=2)
    except ValueError:
        await update.message.reply_text(
            "⛔ 代理 ID 必须是整数。",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    # 3. Lecture des proxies
    proxies = await storage_manager.read_data(PROXIES_FILE)
    initial_count = len(proxies)

    # 4. Suppression via filtrage
    new_proxies = [p for p in proxies if p.get('id') != target_id]

    # 5. Vérification si trouvé
    if len(new_proxies) == initial_count:
        await update.message.reply_text(
            rf"⚠️ 未找到代理 ID `{safe_id}`。",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    # 6. Sauvegarde
    await storage_manager.write_data(PROXIES_FILE, new_proxies)

    logger.info(f"Proxy ID {target_id} supprimé par {update.effective_user.username}")

    # 7. Confirmation utilisateur
    await update.message.reply_text(
        rf"🗑️ 代理 ID **`{safe_id}`** 已成功删除。",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=get_main_menu_keyboard()
    )
