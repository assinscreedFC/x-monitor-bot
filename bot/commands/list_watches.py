import logging
from telegram import Update
from telegram.ext import ContextTypes
import asyncio
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from .menu import get_main_menu_keyboard  # <-- IMPORTER LE CLAVIER PRINCIPAL

from core.json_manager import storage_manager, MONITORS_FILE
from core.auth import whitelist_required

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
        reply_markup = None
        if i == len(parts) - 1:
            reply_markup = get_main_menu_keyboard()

        if i > 0:
            # FIX FINAL HEADER : Utilisation de crochets échappés \[ ... \] au lieu de parenthèses
            header = rf"\[继续 \- 第 {i + 1}/{len(parts)} 部分\]\n"

        await update.message.reply_text(header + part, parse_mode=parse_mode, reply_markup=reply_markup)

        if len(parts) > 2:
            await asyncio.sleep(0.5)


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Affiche la liste de toutes les surveillances actives et inactives.
    """
    logger.info(f"Commande /list_watches reçue de {update.effective_user.username}.")

    try:
        monitors = await storage_manager.read_data(MONITORS_FILE)
    except Exception as e:
        # Protection du message d'erreur
        safe_error = escape_markdown(str(e), version=2)
        await update.message.reply_text(
            rf"⛔ 读取监控时发生错误: {safe_error}",
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not monitors:
        await update.message.reply_text(
            "🔎 尚未注册任何监控。",
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Construire le message de réponse
    response_parts = ["📌 **监控列表 (启用/禁用)**\n"]

    for m in monitors:
        # TRADUCTION DES STATUTS (Texte brut sans caractères spéciaux)
        status_raw = "✅ 启用" if m.get('enabled') else "❌ 禁用"
        links_raw = "🔗 是" if m.get('include_links', True) else "🚫 否"

        last_id = m.get('last_post_id', 'INIT')

        # FIX CRITIQUE ICI : Remplacement de "(INIT)" par "- INIT" pour supprimer les parenthèses
        last_status_raw = "新监控 - INIT"

        if last_id and last_id != "INIT":
            # On sépare par un espace simple, pas de caractères spéciaux
            last_status_raw = f"最后帖子日期: {last_id.split('T')[0]}"

        # --- 1. ÉCHAPPEMENT DES VARIABLES ---
        safe_id = escape_markdown(str(m['id']), version=2)
        safe_username = escape_markdown(m['x_account'], version=2)
        safe_chat_id = escape_markdown(str(m['telegram_chat_id']), version=2)

        # --- 2. ÉCHAPPEMENT DES TEXTES ---
        safe_links = escape_markdown(links_raw, version=2)
        safe_last_status = escape_markdown(last_status_raw, version=2)

        # TRADUCTION DE L'ENTRY (Assemblage avec raw string)
        entry = (
            rf"\n\-\-\- 监控 ID: `{safe_id}` \-\-\-\n"
            f"状态: {status_raw}\n"
            f"X 账户: **@{safe_username}**\n"
            f"目标群组 Chat: `{safe_chat_id}`\n"
            rf"选项: \[链接: {safe_links}\] \| \[{safe_last_status}\]\n"
        )
        response_parts.append(entry)

    final_message = "\n".join(response_parts)

    # Utilisation de la nouvelle fonction pour gérer le découpage et le menu
    await send_long_message(
        update,
        final_message,
        parse_mode=ParseMode.MARKDOWN_V2
    )