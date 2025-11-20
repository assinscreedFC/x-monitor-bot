import asyncio
import logging
import time
from telegram import Update
from telegram.ext import ContextTypes
# Pas besoin d'importer ParseMode si on utilise le string 'HTML'
import html

from config import settings
from core.json_manager import storage_manager, MONITORS_FILE
from core.auth import whitelist_required
from .menu import get_main_menu_keyboard

# On récupère le logger global
logger = logging.getLogger('TelegramBot')


async def _get_next_monitor_id(monitors_list: list) -> int:
    """
    Calcule l'ID unique suivant en se basant sur le max(id) actuel.
    """
    if not monitors_list:
        return 1
    max_id = max(item.get('id', 0) for item in monitors_list)
    return max_id + 1


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ajoute une nouvelle surveillance de compte X vers un chat Telegram.
    Format: /add_watch <@compte_x> <chat_id> [inclure_liens: true/false]
    """
    user = update.effective_user
    logger.info(f"Commande /add_watch reçue de {user.username} ({user.id})")

    # 1. Valider les arguments
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "用法: <code>/add_watch &lt;@X账户&gt; &lt;ChatID&gt; [inclure_liens: true/false]</code>\n"
            "示例: <code>/add_watch @NASA -100123456789 true</code>",
            reply_markup=get_main_menu_keyboard(),
            parse_mode='HTML'  # <-- Utilisation directe du string
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
            # CORRECTION DU WARNING : 'inclure_liens' sans antislash
            await update.message.reply_text(
                "⚠️ 'inclure_liens' 参数无效。请使用 'true' 或 'false'.",
                reply_markup=get_main_menu_keyboard(),
                parse_mode='HTML'
            )
            return

    # 3. Lire la base de données
    monitors_data = await storage_manager.read_data(MONITORS_FILE)

    # 4. Vérifier les doublons
    for monitor in monitors_data:
        if monitor.get('x_account') == x_account and monitor.get('telegram_chat_id') == telegram_chat_id:
            safe_account = html.escape(x_account)
            safe_chat = html.escape(telegram_chat_id)

            await update.message.reply_text(
                f"⚠️ 监控 (<code>@{safe_account}</code> -> <code>{safe_chat}</code>) 已存在.",
                reply_markup=get_main_menu_keyboard(),
                parse_mode='HTML'
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

    safe_id = html.escape(str(new_id))
    safe_account = html.escape(x_account)
    safe_chat = html.escape(telegram_chat_id)

    await update.message.reply_text(
        f"✅ 监控添加成功！\n"
        f"ID: <b>{safe_id}</b>\n"
        f"X 账户: <b>@{safe_account}</b>\n"
        f"Telegram 群组: <b>{safe_chat}</b>\n"
        f"包含链接: <b>{links_text}</b>",
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )