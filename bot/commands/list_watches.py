import logging
from telegram import Update
from telegram.ext import ContextTypes
import asyncio
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from .menu import get_main_menu_keyboard
import html
from core.json_manager import storage_manager, MONITORS_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')

# Constante Telegram pour la limite de message
TELEGRAM_MAX_MESSAGE_LENGTH = 4096


async def send_long_message(update: Update, text: str, parse_mode: str = None):
    """
    Découpe et envoie un long message.
    Sécurisé : Utilise des crochets [ ] pour l'en-tête au lieu de parenthèses.
    """
    parts = []
    current_part = ""
    lines = text.split('\n')

    for line in lines:
        if len(current_part) + len(line) + 1 > TELEGRAM_MAX_MESSAGE_LENGTH:
            parts.append(current_part.strip())
            current_part = line + '\n'
        else:
            current_part += line + '\n'

    if current_part:
        parts.append(current_part.strip())

    for i, part in enumerate(parts):
        header = ""
        reply_markup = None
        if i == len(parts) - 1:
            reply_markup = get_main_menu_keyboard()

        if i > 0:
            # SÉCURITÉ : Utilisation de crochets échappés.
            # Telegram accepte mieux \[...\] que les parenthèses dans certains contextes.
            header = rf"\[继续 \- 第 {i + 1}/{len(parts)} 部分\]\n"

        await update.message.reply_text(header + part, parse_mode=parse_mode, reply_markup=reply_markup)

        if len(parts) > 2:
            await asyncio.sleep(0.5)


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Commande /list_watches reçue de {update.effective_user.username}.")

    try:
        monitors = await storage_manager.read_data(MONITORS_FILE)
    except Exception as e:
        safe_error = html.escape(str(e))
        await update.message.reply_text(
            f"⛔ 读取监控时发生错误: {safe_error}",
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return

    if not monitors:
        await update.message.reply_text(
            "🔎 尚未注册任何监控。",
            reply_markup=get_main_menu_keyboard()
        )
        return

    # En-tête en HTML (les parenthèses ne posent pas de problème)
    response_parts = ["<b>📌 监控列表 (启用/禁用)</b>\n"]

    for m in monitors:
        status_raw = "✅ 启用" if m.get('enabled') else "❌ 禁用"
        links_raw = "🔗 是" if m.get('include_links', True) else "🚫 否"
        last_id = m.get('last_post_id', 'INIT')

        last_status_raw = "新监控 - INIT"
        if last_id and last_id != "INIT":
            last_status_raw = f"最后帖子日期: {last_id.split('T')[0]}"

        # Échapper uniquement les valeurs dynamiques pour HTML
        safe_id = html.escape(str(m.get('id', '')))
        safe_username = html.escape(m.get('x_account', ''))
        safe_chat_id = html.escape(str(m.get('telegram_chat_id', '')))

        safe_links = html.escape(links_raw)
        safe_last_status = html.escape(last_status_raw)

        # Construire l'entrée en HTML (utilisation de <b> et <code> pour le format)
        entry = (
            f"\n--- 监控 ID: <code>{safe_id}</code> ---\n"
            f"状态: {status_raw}\n"
            f"X 账户: <b>@{safe_username}</b>\n"
            f"目标群组 Chat: <code>{safe_chat_id}</code>\n"
            f"选项: [链接: {safe_links}] | [{safe_last_status}]\n"
        )
        response_parts.append(entry)

    final_message = "\n".join(response_parts)

    await send_long_message(
        update,
        final_message,
        parse_mode=ParseMode.HTML
    )