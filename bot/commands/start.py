from telegram import Update
from telegram.ext import ContextTypes
import logging

# On utilise le logger configuré dans config/settings.py
logger = logging.getLogger('TelegramBot')


async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Répond un simple message de "pong" quand on tape /start.
    C'est notre test pour voir si le bot est vivant.
    """
    user = update.effective_user
    logger.info(f"Commande /start reçue de {user.username} (ID: {user.id})")

    await update.message.reply_text(
        # Correction de l'encodage
        f"🤖 Bot Opérationnel !\n" 
        f"Bonjour, {user.first_name}.\n"
        f"Ceci est le point d'entrée pour le moniteur X/Twitter."
    )