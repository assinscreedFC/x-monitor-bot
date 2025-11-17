import logging
from telegram.ext import Application, ApplicationBuilder
from config import settings  # Importe notre config (token)
from bot.handler import register_handlers  # Importe notre routeur

# On récupère le logger global
logger = logging.getLogger('TelegramBot')


def setup_bot() -> Application:
    """
    Construit et configure l'instance de l'application Telegram.
    Ne lance pas le bot, il ne fait que le préparer.
    """
    logger.info("Configuration de l'application Telegram...")

    # Vérification (déjà faite dans settings.py, mais double sécurité)
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.critical("Le TELEGRAM_BOT_TOKEN n'est pas chargé.")
        raise ValueError("Token Telegram manquant.")

    # Construit l'application
    app = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .read_timeout(30)  # Temps max pour une réponse de Telegram
        .write_timeout(30)  # Temps max pour envoyer un message
        .build()
    )

    # Attache toutes nos commandes (depuis handler.py)
    register_handlers(app)

    logger.info("Application Telegram configurée avec les handlers.")

    return app