import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode # <-- Pour le formatage
from telegram.helpers import escape_markdown # <-- Pour l'échappement
from .menu import get_main_menu_keyboard  # <-- Import du clavier principal

from core.json_manager import storage_manager, PROXIES_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')

@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Supprime un proxy par son ID.
    Usage: /proxy_remove <ID_du_proxy>
    """
    # 1. Vérifier l'usage (TRADUCTION)
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            r"用法: /proxy\_remove <代理\_ID> (使用 /proxy\_list 查看 ID)",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard() # <-- ATTACHER LE MENU
        )
        return

    # 2. Valider l'ID
    try:
        target_id = int(context.args[0])
        safe_id = escape_markdown(str(target_id), version=2)
    except ValueError:
        # TRADUCTION DE L'ERREUR DE VALEUR
        await update.message.reply_text(
            "⛔ ID 必须是一个整数。",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard() # <-- ATTACHER LE MENU
        )
        return

    # 3. Lire les données
    proxies = await storage_manager.read_data(PROXIES_FILE)
    initial_count = len(proxies)

    # 4. Trouver et filtrer le proxy à supprimer
    # Nouvelle liste SANS l'ID ciblé
    new_proxies = [p for p in proxies if p.get('id') != target_id]

    # 5. Vérifier le résultat
    if len(new_proxies) == initial_count:
        # TRADUCTION DU MESSAGE NON TROUVÉ
        await update.message.reply_text(
            rf"⚠️ 代理 ID `{safe_id}` 未找到\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard() # <-- ATTACHER LE MENU
        )
        return

    # 6. Sauvegarder la nouvelle liste
    await storage_manager.write_data(PROXIES_FILE, new_proxies)

    logger.info(f"Proxy ID {target_id} retiré par {update.effective_user.username}")
    # TRADUCTION DU MESSAGE DE SUCCÈS
    await update.message.reply_text(
        rf"🗑️ 代理 ID **`{safe_id}`** 已从列表中移除\.",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=get_main_menu_keyboard() # <-- ATTACHER LE MENU
    )