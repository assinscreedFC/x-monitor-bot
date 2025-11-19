import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from .menu import get_main_menu_keyboard  # <-- Import du clavier principal

from core.json_manager import storage_manager, WHITELIST_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Retire un utilisateur de la whitelist.
    Usage: /whitelist_remove <user_id>
    """
    # 1. Vérification de l'usage (TRADUCTION)
    if not context.args:
        await update.message.reply_text(
            r"用法: /whitelist\_remove <Telegram 用户 ID>",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
        )
        return

    # 2. Validation de l'ID
    try:
        # L'ID doit être un nombre entier
        target_id = int(context.args[0])
        safe_id = escape_markdown(str(target_id), version=2)  # Échapper l'ID pour les messages
    except ValueError:
        # TRADUCTION DE L'ERREUR DE VALEUR
        await update.message.reply_text(
            "⛔ 用户 ID 必须是一个整数。",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
        )
        return

    user_id = update.effective_user.id

    # 3. Lecture des données
    whitelist = await storage_manager.read_data(WHITELIST_FILE)

    # Crée une nouvelle liste sans l'utilisateur ciblé
    new_whitelist = [user for user in whitelist if user.get('user_id') != target_id]

    # Vérification si un utilisateur a été retiré
    removed_count = len(whitelist) - len(new_whitelist)

    if removed_count == 0:
        # TRADUCTION : Aucun utilisateur trouvé
        await update.message.reply_text(
            rf"⚠️ 白名单中未找到 ID 为 `{safe_id}` 的用户。",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
        )
        return

    # Vérification critique : Empêcher de retirer le dernier admin
    if len(new_whitelist) == 0:
        # TRADUCTION : Impossible de retirer le dernier administrateur
        await update.message.reply_text(
            rf"🚫 无法移除 ID 为 `{safe_id}` 的用户。移除最后一个管理员将使机器人无法使用。",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
        )
        return

    # Mise à jour du fichier JSON
    await storage_manager.write_data(WHITELIST_FILE, new_whitelist)

    logger.info(f"Admin retiré: ID {target_id} par {update.effective_user.username}")

    # TRADUCTION : Succès
    await update.message.reply_text(
        rf"✅ ID 为 `{safe_id}` 的用户已从白名单中移除。",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
    )