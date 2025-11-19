import asyncio
import logging
import time
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown

from config import settings
from core.json_manager import storage_manager, MONITORS_FILE
from core.auth import whitelist_required
from .menu import get_main_menu_keyboard

logger = logging.getLogger('TelegramBot')


async def _get_next_monitor_id(monitors_list: list) -> int:
    """
    Calcule l'ID unique suivant en se basant sur le max(id) actuel.
    """
    if not monitors_list:
        return 1
    return max(item.get('id', 0) for item in monitors_list) + 1


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ajoute une nouvelle surveillance de compte X vers un chat Telegram.
    Format: /add_watch <@compte_x> <chat_id> [inclure_liens: true/false]
    """
    user = update.effective_user
    logger.info(f"Commande /add_watch reçue de {user.username} ({user.id})")

    # 1. Vérifier les arguments
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            r"用法: /add_watch <@X账户> <ChatID> [inclure\_liens: true/false]\n"
            r"示例: /add_watch @NASA -100123456789 true",
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    x_account = context.args[0].replace('@', '').strip()
    telegram_chat_id = context.args[1].strip()

    # 2. Argument optionnel 'include_links'
    include_links_status = getattr(settings, "INCLUDE_LINKS_DEFAULT", True)
    if len(context.args) > 2:
        link_arg = context.args[2].lower()
        if link_arg in ['true', 'on', 'yes']:
            include_links_status = True
        elif link_arg in ['false', 'off', 'no']:
            include_links_status = False
        else:
            await update.message.reply_text(
                r"⚠️ 'inclure\_liens' 参数无效。请使用 'true' 或 'false'\.",
                reply_markup=get_main_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

    # 3. Lire la base de données
    monitors_data = await storage_manager.read_data(MONITORS_FILE)

    # 4. Vérifier les doublons
    for monitor in monitors_data:
        if monitor.get('x_account') == x_account and monitor.get('telegram_chat_id') == telegram_chat_id:
            await update.message.reply_text(
                rf"⚠️ 监控 (@{escape_markdown(x_account, 2)} -> {escape_markdown(telegram_chat_id, 2)}) 已存在\.",
                reply_markup=get_main_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

    # 5. Générer le nouvel objet Monitor
    new_id = await _get_next_monitor_id(monitors_data)
    new_monitor = {
        "id": new_id,
        "x_account": x_account,
        "telegram_chat_id": telegram_chat_id,
        "include_links": include_links_status,
        "enabled": True,
        "last_post_id": "INIT",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    # 6. Ajouter et sauvegarder
    monitors_data.append(new_monitor)
    await storage_manager.write_data(MONITORS_FILE, monitors_data)

    logger.info(f"Nouvelle surveillance (ID: {new_id}) ajoutée par {user.username}")

    # 7. Message de confirmation
    links_text = "是 (Oui)" if include_links_status else "否 (Non)"
    safe_id = escape_markdown(str(new_id), 2)
    safe_account = escape_markdown(x_account, 2)
    safe_chat = escape_markdown(telegram_chat_id, 2)

    await update.message.reply_text(
        rf"✅ 监控添加成功！\n"
        rf"ID: **{safe_id}**\n"
        rf"X 账户: **@{safe_account}**\n"
        rf"Telegram 群组: **{safe_chat}**\n"
        rf"包含链接: **{links_text}**",
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )
