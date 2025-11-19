import logging
from telegram import Update
from telegram.ext import ContextTypes
import asyncio
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from .menu import get_main_menu_keyboard  # <-- 1. IMPORTER LE CLAVIER PRINCIPAL

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

    # Tentative de découper par lignes pour ne pas couper au milieu d'un moniteur
    lines = text.split('\n')

    # Logique de découpage (inchangée)
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
            reply_markup = get_main_menu_keyboard()  # <-- 2. ATTACHER LE CLAVIER FINAL

        if i > 0:
            # Le header est en chinois maintenant
            header = rf"**\(继续 \- 第 {i + 1}/{len(parts)} 部分\)**\n"

        await update.message.reply_text(header + part, parse_mode=parse_mode, reply_markup=reply_markup)

        # Petite pause pour éviter le flood si la liste est très longue
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
        await update.message.reply_text(
            f"⛔ 读取监控时发生错误: {e}",
            reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
        )
        return

    if not monitors:
        await update.message.reply_text(
            "🔎 尚未注册任何监控。",  # <-- TRADUCTION
            reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
        )
        return

    # Construire le message de réponse
    response_parts = ["📌 **监控列表 (启用/禁用)**\n"]  # <-- TRADUCTION

    for m in monitors:
        # TRADUCTION DES STATUTS
        status = "✅ 启用" if m.get('enabled') else "❌ 禁用"
        links = "🔗 是 (Oui)" if m.get('include_links', True) else "🚫 否 (Non)"

        # --- 3. CORRECTION DE L'ÉCHAPPEMENT ET MISE À JOUR ---
        last_id = m.get('last_post_id', 'INIT')
        last_status = "新监控 (INIT)"  # <-- TRADUCTION
        if last_id and last_id != "INIT":
            last_status = f"最后帖子日期: {last_id.split('T')[0]}"  # <-- TRADUCTION

        # On échappe TOUT ce qui vient du JSON
        safe_id = escape_markdown(str(m['id']), version=2)
        safe_username = escape_markdown(m['x_account'], version=2)
        safe_chat_id = escape_markdown(str(m['telegram_chat_id']), version=2)
        safe_last_status = escape_markdown(last_status, version=2)

        # TRADUCTION DE L'ENTRY
        entry = (
            rf"\n\-\-\- 监控 ID: `{safe_id}` \-\-\-\n"
            f"状态: {status}\n"
            f"X 账户: **@{safe_username}**\n"
            f"目标群组 Chat: `{safe_chat_id}`\n"
            rf"选项: \[链接: {links}\] \| \[{safe_last_status}\]\n"
        )
        response_parts.append(entry)

    final_message = "\n".join(response_parts)

    # Utilisation de la nouvelle fonction pour gérer le découpage et le menu
    await send_long_message(
        update,
        final_message,
        parse_mode=ParseMode.MARKDOWN_V2
    )