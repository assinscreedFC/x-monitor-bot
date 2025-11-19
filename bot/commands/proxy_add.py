import logging
import re
import time
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from .menu import get_main_menu_keyboard # <-- Import du clavier principal

from core.json_manager import storage_manager, PROXIES_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')

# Regex pour valider le format IP:PORT ou DOMAIN:PORT (sans l'authentification)
PROXY_REGEX = re.compile(r"^(?:https?://)?([\w\.\-]+:\d{2,5})$", re.IGNORECASE)


async def _get_next_id():
    """Détermine le prochain ID unique pour un nouveau proxy."""
    data = await storage_manager.read_data(PROXIES_FILE)
    if not data:
        return 1
    # Utiliser str() car .get() peut retourner None ou int, et nous voulons max sur les int
    return max(int(p.get('id', 0)) for p in data) + 1


async def _add_proxy_to_json(proxy_url_clean: str):
    """Ajoute le proxy au fichier JSON avec les métadonnées initiales."""

    data = await storage_manager.read_data(PROXIES_FILE)
    new_id = await _get_next_id()

    new_proxy = {
        "id": new_id,
        "proxy_url": proxy_url_clean,
        "active": True,
        "error_count": 0,
        "last_used": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    data.append(new_proxy)
    await storage_manager.write_data(PROXIES_FILE, data)
    return new_id, proxy_url_clean


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ajoute un proxy à la liste de rotation.
    Usage: /proxy_add <ip:port> (l'authentification est gérée par le .env)
    """
    # 1. Vérifier les arguments (TRADUCTION DE L'USAGE)
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            rf"⛔ 代理格式无效。请使用 `ip:port` 或 `http://ip:port` 格式\."
    rf" 请勿在此处包含用户名和密码 \(它们在 \.env 文件中\)\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard() # <-- ATTACHER LE MENU
        )
        return

    raw_url = context.args[0].strip()

    # 2. Validation de l'URL pour s'assurer qu'elle ne contient pas l'authentification
    match = PROXY_REGEX.match(raw_url)

    if not match:
        # TRADUCTION DU MESSAGE D'ERREUR DE FORMAT
        await update.message.reply_text(
            "⛔ 代理格式无效。请使用 `ip:port` 或 `http://ip:port` 格式。\n"
            "请勿在此处包含用户名和密码 (它们在 .env 文件中)。",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard() # <-- ATTACHER LE MENU
        )
        return

    proxy_url_clean = raw_url

    try:
        new_id, url_added = await _add_proxy_to_json(proxy_url_clean)

        # Échapper l'URL et l'ID pour le message final
        safe_id = escape_markdown(str(new_id), version=2)
        safe_url = escape_markdown(url_added, version=2)

        # MESSAGE DE SUCCÈS (TRADUCTION)
        await update.message.reply_text(
            rf"✅ 代理添加成功 (ID: **{safe_id}**)\n"
            rf"地址: `{safe_url}`\n"
            rf"认证方式: 使用配置文件中的 `PROXY\_AUTH\_USERNAME`\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard() # <-- ATTACHER LE MENU
        )
        logger.info(f"Nouveau proxy ajouté (ID: {new_id}, URL: {url_added}) par {update.effective_user.username}")

    except Exception as e:
        logger.exception(f"Erreur lors de l'ajout du proxy: {e}")
        # MESSAGE D'ERREUR INTERNE (TRADUCTION)
        await update.message.reply_text(
            "内部错误：添加代理时发生错误。",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard() # <-- ATTACHER LE MENU
        )