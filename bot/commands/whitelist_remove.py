import logging
from telegram import Update
from telegram.ext import ContextTypes

from core.json_manager import storage_manager, WHITELIST_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Retire un utilisateur de la whitelist.
    Usage: /whitelist_remove <user_id>
    """
    if not context.args:
        await update.message.reply_text("Usage: /whitelist_remove <ID_utilisateur_Telegram>")
        return

    try:
        # L'ID doit être un nombre entier
        target_id = int(context.args[0])
    except ValueError:
        # Correction de l'encodage
        await update.message.reply_text("⛔ L'ID utilisateur doit être un nombre entier.")
        return

    # Empêcher l'utilisateur de se retirer lui-même s'il est le dernier admin
    user_id = update.effective_user.id

    # Lecture des données
    whitelist = await storage_manager.read_data(WHITELIST_FILE)

    # Crée une nouvelle liste sans l'utilisateur ciblé
    new_whitelist = [user for user in whitelist if user.get('user_id') != target_id]

    # Vérification si un utilisateur a été retiré
    removed_count = len(whitelist) - len(new_whitelist)

    if removed_count == 0:
        # Correction de l'encodage
        await update.message.reply_text(f"⚠️ Aucun utilisateur trouvé avec l'ID {target_id} dans la whitelist.")
        return

    # Vérification critique : Empêcher de retirer le dernier admin
    if len(new_whitelist) == 0:
        # Correction de l'encodage
        await update.message.reply_text(
            f"🚫 Impossible de retirer l'utilisateur ID {target_id}. Le retrait du dernier administrateur rendrait le bot inutilisable."
        )
        return

    # Mise à jour du fichier JSON
    await storage_manager.write_data(WHITELIST_FILE, new_whitelist)

    logger.info(f"Admin retiré: ID {target_id} par {update.effective_user.username}")
    # Correction de l'encodage
    await update.message.reply_text(f"✅ Utilisateur avec l'ID {target_id} retiré de la whitelist.")