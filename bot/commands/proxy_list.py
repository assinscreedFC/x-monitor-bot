import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
import asyncio
from telegram.helpers import escape_markdown

from core.json_manager import storage_manager, PROXIES_FILE
from core.auth import whitelist_required
from .menu import get_main_menu_keyboard

logger = logging.getLogger('TelegramBot')

TELEGRAM_MAX_MESSAGE_LENGTH = 4096


async def send_long_message(update: Update, text: str, parse_mode: str = None):
    """
    Envoie un long message découpé en plusieurs parties.
    Le clavier principal n'est attaché qu'au dernier message.
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
        reply_markup = get_main_menu_keyboard() if i == len(parts) - 1 else None

        header = ""
        if i > 0:
            header = rf"\[继续 \- 第 {i + 1}/{len(parts)} 部分\]\n"

        await update.message.reply_text(
            header + part,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )

        if len(parts) > 2:
            await asyncio.sleep(0.5)


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Affiche la liste des proxies enregistrés.
    """
    logger.info(f"Commande /proxy_list reçue de {update.effective_user.username}.")

    try:
        proxies = await storage_manager.read_data(PROXIES_FILE)
    except Exception as e:
        await update.message.reply_text(
            f"⛔ 读取代理时发生错误: {escape_markdown(str(e), version=2)}",
            reply_markup=get_main_menu_keyboard()
        )
        return

    if not proxies:
        await update.message.reply_text(
            "🔎 尚未注册任何代理。",
            reply_markup=get_main_menu_keyboard()
        )
        return

    response_parts = ["📡 **已注册代理列表**\n"]

    for p in proxies:
        status = "✅ 启用" if p.get('active') else "❌ 禁用"
        errors = p.get('error_count', 0)

        url_display = p.get('proxy_url', '')
        if len(url_display) > 50:
            url_display = url_display[:30] + "..." + url_display[-10:]

        safe_url = escape_markdown(url_display, version=2)
        safe_id = escape_markdown(str(p.get('id')), version=2)
        last_used = p.get('last_used', 'N/A')
        safe_date = escape_markdown(last_used.split('T')[0], version=2)

        entry = (
            rf"\-\-\- 代理 ID: `{safe_id}` \-\-\-\n"
            f"状态: **{status}**\n"
            f"URL: `{safe_url}`\n"
            rf"错误: {errors} 🚫 \| 最后使用: {safe_date}\n"
        )

        response_parts.append(entry)

    final_message = "\n".join(response_parts)

    await send_long_message(
        update,
        final_message,
        parse_mode=ParseMode.MARKDOWN_V2
    )
