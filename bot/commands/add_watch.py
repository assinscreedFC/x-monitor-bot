import asyncio
import logging
import time
from telegram import Update
from telegram.ext import ContextTypes
import html

from config import settings
from core.json_manager import storage_manager, MONITORS_FILE
from core.auth import whitelist_required
from .menu import get_main_menu_keyboard

logger = logging.getLogger('TelegramBot')


def escape_for_html(text: str) -> str:
    """
    Échappe le texte pour l'envoyer en parse_mode='HTML' chez Telegram.
    On utilise html.escape puis on remplace les parenthèses (et autres si besoin)
    par leurs entités pour éviter les erreurs du parser d'entités.
    """
    if text is None:
        return ''
    escaped = html.escape(str(text))
    # Telegram peut parfois rejeter certains caractères — on les convertit en entités HTML sûres
    escaped = escaped.replace('(', '&#40;').replace(')', '&#41;')
    # &lt; &gt; &amp; " ' sont déjà traités par html.escape
    return escaped


async def _get_next_monitor_id(monitors_list: list) -> int:
    if not monitors_list:
        return 1
    max_id = max(item.get('id', 0) for item in monitors_list)
    return max_id + 1


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"Commande /add_watch reçue de {user.username} ({user.id})")

    # 1. Valider les arguments
    if not context.args or len(context.args) < 2:
        # Construire le bloc d'usage en échappant d'abord le texte interne,
        # puis l'entourer d'un <pre> pour conserver la mise en forme.
        usage_inner = "/add_watch <@X_account> <ChatID> [include_links: true/false]\nEx: /add_watch @NASA -100123456789 true"
        usage_html = "<pre>" + html.escape(usage_inner) + "</pre>"

        await update.message.reply_text(
            usage_html,
            reply_markup=get_main_menu_keyboard(),
            parse_mode='HTML'
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
            safe_account = escape_for_html(x_account)
            safe_chat = escape_for_html(telegram_chat_id)

            # utiliser -> en texte simple (il sera échappé ci-dessous)
            duplicate_msg = f"⚠️ 监控 (<code>@{safe_account}</code> -&gt; <code>{safe_chat}</code>) 已存在."
            # note : on a remplacé '>' par '&gt;' dans la flèche pour plus de sûreté
            await update.message.reply_text(
                duplicate_msg,
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

    # 7. Message de confirmation — tout ce qui est injecté est échappé
    links_text = "是 (Oui)" if include_links_status else "否 (Non)"
    safe_id = escape_for_html(str(new_id))
    safe_account = escape_for_html(x_account)
    safe_chat = escape_for_html(telegram_chat_id)
    safe_links_text = escape_for_html(links_text)

    confirmation = (
        f"✅ 监控添加成功！\n"
        f"ID: <b>{safe_id}</b>\n"
        f"X 账户: <b>@{safe_account}</b>\n"
        f"Telegram 群组: <b>{safe_chat}</b>\n"
        f"包含链接: <b>{safe_links_text}</b>"
    )

    await update.message.reply_text(
        confirmation,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='HTML'
    )
