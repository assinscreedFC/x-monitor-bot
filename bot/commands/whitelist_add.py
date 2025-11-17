import logging
from telegram import Update
from telegram.ext import ContextTypes
import time

from core.json_manager import storage_manager, WHITELIST_FILE

logger = logging.getLogger('TelegramBot')


async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ajoute un utilisateur à la whitelist.
    Usage: /whitelist_add <user_id_ou_username>
    NOTE: Cette commande est déprotégée pour permettre l'ajout du premier admin.
    """
    user_id_or_username = context.args[0] if context.args else None
    whitelist = await storage_manager.read_data(WHITELIST_FILE)

    if not user_id_or_username:
        await update.message.reply_text("Usage: /whitelist_add <ID_utilisateur_Telegram_ou_@username>")
        return

    target_id = None
    target_username = None

    # 1. Tenter de convertir en ID
    try:
        target_id = int(user_id_or_username)
    except ValueError:
        # Si la conversion échoue, on suppose que c'est un nom d'utilisateur
        if user_id_or_username.startswith('@'):
            target_username = user_id_or_username.replace('@', '')
        else:
            await update.message.reply_text("ID utilisateur ou nom d'utilisateur invalide.")
            return

    # 2. Gérer l'ajout du demandeur si l'ID n'est pas fourni (cas du premier admin)
    if target_id is None:
        target_id = update.effective_user.id
        # Si on a un username fourni, on le garde. Sinon, on prend celui du demandeur.
        if not target_username:
            target_username = update.effective_user.username

    # 3. Vérifier les doublons
    if any(user.get('user_id') == target_id for user in whitelist):
        await update.message.reply_text(f"⚠️ L'utilisateur avec l'ID {target_id} est déjà whitelisté.")
        return  # <-- SORTIE SI DOUBLON

    # 4. Ajouter l'utilisateur
    new_user_entry = {
        "user_id": target_id,
        "username": target_username or str(target_id),
        "added_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    whitelist.append(new_user_entry)
    await storage_manager.write_data(WHITELIST_FILE, whitelist)

    logger.info(f"Admin ajouté: ID {target_id} par {update.effective_user.username}")
    await update.message.reply_text(
        f"✅ Utilisateur {target_username or target_id} ajouté à la whitelist.\n"
        f"Les commandes sensibles sont maintenant actives."
    )