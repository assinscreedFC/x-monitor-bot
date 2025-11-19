import logging
import re
import time
import html  # <-- IMPORT CORRECT
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from .menu import get_main_menu_keyboard
from core.json_manager import storage_manager, PROXIES_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')

PROXY_REGEX = re.compile(r"^(?:https?://)?([\w\.\-]+:\d{2,5})$", re.IGNORECASE)


async def _get_next_id():
    data = await storage_manager.read_data(PROXIES_FILE)
    if not data:
        return 1
    return max(int(p.get("id", 0)) for p in data) + 1


async def _add_proxy_to_json(proxy_url: str):
    data = await storage_manager.read_data(PROXIES_FILE)
    new_id = await _get_next_id()
    new_proxy = {
        "id": new_id,
        "proxy_url": proxy_url,
        "active": True,
        "error_count": 0,
        "last_used": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    data.append(new_proxy)
    await storage_manager.write_data(PROXIES_FILE, data)
    return new_id, proxy_url


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "⛔ 代理格式无效。请使用 <code>ip:port</code> 或 <code>http://ip:port</code> 格式。\n"
            "请勿在此处包含用户名和密码 (它们在 .env 文件中)。",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
        )
        return

    raw_url = context.args[0].strip()
    if not PROXY_REGEX.match(raw_url):
        await update.message.reply_text(
            "⛔ 代理格式无效。请使用 <code>ip:port</code> 或 <code>http://ip:port</code> 格式。\n"
            "请勿在此处包含用户名和密码 (它们在 .env 文件中)。",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
        )
        return

    try:
        new_id, url_added = await _add_proxy_to_json(raw_url)
        safe_id = html.escape(str(new_id))   # <-- UTILISATION DE html.escape
        safe_url = html.escape(url_added)

        await update.message.reply_text(
            f"✅ 代理添加成功 (ID: <b>{safe_id}</b>)\n"
            f"地址: <code>{safe_url}</code>\n"
            f"认证方式: 使用配置文件中的 <code>PROXY_AUTH_USERNAME</code>。",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
        )

        logger.info(f"Nouveau proxy ajouté (ID: {new_id}, URL: {url_added}) par {update.effective_user.username}")

    except Exception as e:
        logger.exception(f"Erreur lors de l'ajout du proxy: {e}")
        await update.message.reply_text(
            "内部错误：添加代理时发生错误。",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
        )
