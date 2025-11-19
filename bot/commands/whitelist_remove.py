import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from .menu import get_main_menu_keyboard

from core.json_manager import storage_manager, WHITELIST_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Retire un utilisateur de la whitelist.
    Usage: /whitelist_remove <user_id>
    """
    # --- 1. Vérification de l'usage ---
    if not context.args:
        await update.message.reply_text(
            r"用法: `/whitelist_remove <Telegram 用户 ID>`",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    # --- 2. Validation de l'ID numérique ---
    try:
        target_id = int(context.args[0])
        safe_id = escape_markdown(str(target_id), version=2)
    except ValueError:
        await update.message.reply_text(
            r"⛔ 用户 ID 必须是整数\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    requester_id = update.effective_user.id

    # --- 3. Lecture de la whitelist ---
    whitelist = await storage_manager.read_data(WHITELIST_FILE)

    # Vérifier si l'utilisateur existe
    if not any(user.get('user_id') == target_id for user in whitelist):
        await update.message.reply_text(
            rf"⚠️ 白名单中未找到 ID `{safe_id}` 的用户\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    # --- 4. Vérification : empêcher de supprimer le dernier admin ---
    if len(whitelist) == 1:
        await update.message.reply_text(
            rf"🚫 无法移除 ID `{safe_id}` 的用户\. 这是最后一个管理员，移除后机器人将无法使用\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    # --- 5. Empêcher un admin de se supprimer lui-même si cela casserait le système ---
    if target_id == requester_id and len(whitelist) == 2:
        await update.message.reply_text(
            rf"🚫 无法移除用户 `{safe_id}`\. 您是仅剩的两个管理员之一，不能自我移除\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    # --- 6. Suppression ---
    new_whitelist = [user for user in whitelist if user.get('user_id') != target_id]

    await storage_manager.write_data(WHITELIST_FILE, new_whitelist)

    logger.info(f"Admin retiré: ID {target_id} par {update.effective_user.username}")

    # --- 7. Succès ---
    await update.message.reply_text(
        rf"✅ ID `{safe_id}` 的用户已从白名单移除\.",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=get_main_menu_keyboard()
    )
