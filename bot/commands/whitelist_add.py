import logging
import time
from telegram import Update
from telegram.constants import ParseMode

from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from .menu import get_main_menu_keyboard  # <-- Import du clavier principal

from core.json_manager import storage_manager, WHITELIST_FILE

logger = logging.getLogger('TelegramBot')


async def _check_and_add_user(update: Update, target_id: int, target_username: str):
    """
    Vérifie les doublons et ajoute l'utilisateur à la whitelist.
    """
    user_info_display = target_username or str(target_id)
    safe_user_info = escape_markdown(user_info_display, version=2)

    whitelist = await storage_manager.read_data(WHITELIST_FILE)

    # 1. Vérifier les doublons
    if any(user.get('user_id') == target_id for user in whitelist):
        await update.message.reply_text(
            rf"⚠️ 用户 ID `{target_id}` 已经是白名单成员\.",  # TRADUCTION : Déjà whitelisté
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    # 2. Ajouter l'utilisateur
    new_user_entry = {
        "user_id": target_id,
        # Si un nom d'utilisateur a été fourni, on le garde. Sinon on utilise l'ID.
        "username": target_username or str(target_id),
        "added_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    whitelist.append(new_user_entry)
    await storage_manager.write_data(WHITELIST_FILE, whitelist)

    logger.info(f"Admin ajouté: ID {target_id} par {update.effective_user.username}")
    await update.message.reply_text(
        rf"✅ 用户 **{safe_user_info}** 已添加到白名单\.\n"  # TRADUCTION : Ajouté
        rf"敏感命令现已启用\.",  # TRADUCTION : Commandes sensibles actives
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=get_main_menu_keyboard()
    )


async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ajoute un utilisateur à la whitelist.
    Usage: /whitelist_add <user_id_ou_username>
    NOTE: Cette commande est déprotégée pour permettre l'ajout du premier admin.
    """
    requester_user = update.effective_user
    target_id = None
    target_username = None

    # --- 1. Gérer le cas sans argument (Ajout du demandeur) ---
    if not context.args:
        # Cas 1: Aucun argument -> on ajoute le demandeur lui-même.
        target_id = requester_user.id
        target_username = requester_user.username

        # Le demandeur doit avoir un username pour l'ajout automatique
        if not target_username:
            await update.message.reply_text(
                r"用法: /whitelist\_add <Telegram 用户 ID> 或 `@username`\n"
    r"**注意:** 如果没有提供参数, 您必须先设置一个 Telegram 用户名才能使用此命令\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=get_main_menu_keyboard()
            )
            return

        await _check_and_add_user(update, target_id, target_username)
        return

    # --- 2. Gérer le cas avec argument ---
    user_id_or_username = context.args[0]

    # Tenter de convertir en ID
    try:
        target_id = int(user_id_or_username)
        target_username = None  # On ne connaît pas le username si on a juste l'ID
    except ValueError:
        # Si la conversion échoue, on suppose que c'est un nom d'utilisateur
        if user_id_or_username.startswith('@'):
            target_username = user_id_or_username.replace('@', '')
        else:
            target_username = user_id_or_username  # Accepter sans @

        # Si c'est un username, on ne peut pas l'ajouter sans connaître l'ID.
        # On doit insister sur l'utilisation de l'ID numérique pour l'ajout.
        await update.message.reply_text(
            rf"⚠️ 仅支持 Telegram 数字 ID \(!\), 因为用户名随时可能更改或无法保证其正确性\.\n"
            rf"请使用 `/whitelist\_add <ID>`\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()
        )
        return

    # --- 3. Exécuter l'ajout (avec ID numérique) ---
    # Si nous sommes ici, target_id est un nombre valide.
    await _check_and_add_user(update, target_id, target_username)