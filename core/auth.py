import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from core.json_manager import storage_manager, WHITELIST_FILE

logger = logging.getLogger('TelegramBot')

async def is_user_whitelisted(user_id: int) -> bool:
    """Vérifie si l'ID utilisateur est dans la whitelist."""
    try:
        whitelist = await storage_manager.read_data(WHITELIST_FILE)
        # La whitelist est une liste de dictionnaires: [{"user_id": 123, "username": "..."}]
        return any(user.get('user_id') == user_id for user in whitelist)
    except Exception as e:
        logger.error(f"Erreur lors de la lecture de la whitelist: {e}")
        # En cas d'erreur DB, on refuse l'accès par sécurité
        return False

def whitelist_required(func):
    """
    Décorateur qui vérifie la permission avant d'exécuter une commande.
    """
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return

        if await is_user_whitelisted(user.id):
            return await func(update, context, *args, **kwargs)
        else:
            logger.warning(f"Accès refusé pour {user.username} (ID: {user.id})")
            await update.message.reply_text("⛔ Vous n'êtes pas autorisé à utiliser cette commande.")
            return
    return wrapped