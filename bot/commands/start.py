import logging
from telegram import Update
from telegram.constants import ParseMode

from telegram.ext import ContextTypes
from .menu import get_main_menu_keyboard # <-- Import du clavier principal

# On utilise le logger configuré dans config/settings.py
logger = logging.getLogger('TelegramBot')


async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Répond un simple message de "pong" quand on tape /start.
    C'est notre test pour voir si le bot est vivant.
    """
    user = update.effective_user
    logger.info(f"Commande /start reçue de {user.username} (ID: {user.id})")

    # TRADUCTION DU MESSAGE
    await update.message.reply_text(
        f"🤖 机器人正在运行！\n"  # Bot Opérationnel !
        f"您好, {user.first_name}.\n"  # Bonjour, {user.first_name}.
        f"这是 X/Twitter 监控器的入口点。",  # Ceci est le point d'entrée pour le moniteur X/Twitter.
        reply_markup=get_main_menu_keyboard(), # <-- ATTACHER LE MENU
    )