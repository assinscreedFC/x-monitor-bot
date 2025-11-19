import logging
import re
import time
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from .menu import get_main_menu_keyboard
from core.json_manager import storage_manager, PROXIES_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')

# Regex pour valider le format IP:PORT ou DOMAIN:PORT (sans auth)
PROXY_REGEX = re.compile(r"^(?:https?://)?([\w\.\-]+:\d{2,5})$", re.IGNORECASE)


async def _get_next_id():
    """Retourne l'ID suivant pour un nouveau proxy."""
    data = await storage_manager.read_data(PROXIES_FILE)
    if not data:
        return 1
    return max(int(p.get("id", 0)) for p in data) + 1


async def _add_proxy_to_json(proxy_url: str):
    """Ajoute le proxy au JSON avec ses métadonnées initiales."""
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
    """
    Ajoute un proxy à la liste de rotation.
    Usage: /proxy_add <ip:port> (auth via .env)
    """
    # 1. Vérification des arguments
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            rf"⛔ 代理格式无效。请使用 `ip:port` 或 `http://ip:port` 格式\."
            rf" 请勿在此处包含用户名和密码 \(它们在 \.env 文件中\)\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    raw_url = context.args[0].strip()

    # 2. Validation du format
    if not PROXY_REGEX.match(raw_url):
        await update.message.reply_text(
            "⛔ 代理格式无效。请使用 `ip:port` 或 `http://ip:port` 格式。\n"
            "请勿在此处包含用户名和密码 (它们在 .env 文件中)。",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    # 3. Ajout du proxy
    try:
        new_id, url_added = await _add_proxy_to_json(raw_url)

        # Échapper les valeurs dynamiques
        safe_id = escape_markdown(str(new_id), version=2)
        safe_url = escape_markdown(url_added, version=2)

        await update.message.reply_text(
            rf"✅ 代理添加成功 (ID: **{safe_id}**)\n"
            rf"地址: `{safe_url}`\n"
            rf"认证方式: 使用配置文件中的 `PROXY\_AUTH\_USERNAME`\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )

        logger.info(f"Nouveau proxy ajouté (ID: {new_id}, URL: {url_added}) par {update.effective_user.username}")

    except Exception as e:
        logger.exception(f"Erreur lors de l'ajout du proxy: {e}")
        await update.message.reply_text(
            "内部错误：添加代理时发生错误。",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
