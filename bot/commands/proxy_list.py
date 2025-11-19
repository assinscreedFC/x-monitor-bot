import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
import asyncio  # Nécessaire pour send_long_message
from telegram.helpers import escape_markdown  # Pour l'échappement des variables

from core.json_manager import storage_manager, PROXIES_FILE
from core.auth import whitelist_required
from .menu import get_main_menu_keyboard  # <-- Import du clavier principal

logger = logging.getLogger('TelegramBot')

# Constante Telegram pour la limite de message
TELEGRAM_MAX_MESSAGE_LENGTH = 4096


async def send_long_message(update: Update, text: str, parse_mode: str = None):
    """
    Découpe et envoie un long message en plusieurs parties pour respecter la limite de Telegram.
    Le clavier principal est attaché à la dernière partie.
    """

    # Découpage du message
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

    # Envoi de chaque partie
    for i, part in enumerate(parts):
        header = ""
        # On attache le menu SEULEMENT au *dernier* message.
        reply_markup = None
        if i == len(parts) - 1:
            reply_markup = get_main_menu_keyboard()  # <-- ATTACHE LE CLAVIER

        if i > 0:
            # Le header est en chinois
            header = rf"**(继续 \- 第 {i + 1}/{len(parts)} 部分)**\n"

        await update.message.reply_text(header + part, parse_mode=parse_mode, reply_markup=reply_markup)

        # Petite pause pour éviter le flood
        if len(parts) > 2:
            await asyncio.sleep(0.5)


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Affiche la liste de tous les proxies enregistrés avec leur statut d'activité et d'erreur.
    """
    logger.info(f"Commande /proxy_list reçue de {update.effective_user.username}.")

    try:
        proxies = await storage_manager.read_data(PROXIES_FILE)
    except Exception as e:
        await update.message.reply_text(
            f"⛔ 读取代理时发生错误: {e}",
            reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
        )
        return

    if not proxies:
        await update.message.reply_text(
            "🔎 尚未注册任何代理。",  # <-- TRADUCTION
            reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
        )
        return

    # Construire le message de réponse
    response_parts = ["📡 **已注册代理列表**\n"]  # <-- TRADUCTION

    for p in proxies:
        # Déterminer le statut et la couleur
        status = "✅ 启用" if p.get('active') else "❌ 禁用"  # <-- TRADUCTION
        errors = p.get('error_count', 0)

        # Affichage (tronqué pour ne pas exposer le mot de passe dans le log Telegram)
        url_display = p['proxy_url']
        if len(url_display) > 50:
            url_display = url_display[:30] + "..." + url_display[-10:]

        # Échapper l'URL pour la rendre sûre en MarkdownV2
        safe_url_display = escape_markdown(url_display, version=2)

        # Échapper l'ID et la date
        safe_id = escape_markdown(str(p['id']), version=2)
        safe_date = escape_markdown(p.get('last_used', 'N/A').split('T')[0], version=2)

        entry = (
            rf"\-\-\- 代理 ID: `{safe_id}` \-\-\-\n"  # <-- TRADUCTION + ÉCHAPPEMENT
            f"状态: **{status}**\n"
            f"URL: `{safe_url_display}`\n"
            rf"错误: {errors} 🚫 \| 最后使用: {safe_date}\n"  # <-- TRADUCTION + ÉCHAPPEMENT
        )
        response_parts.append(entry)

    final_message = "\n".join(response_parts)

    # Utilisation de la fonction helper
    await send_long_message(
        update,
        final_message,
        parse_mode=ParseMode.MARKDOWN_V2  # <-- UTILISER LE BON MODE
    )