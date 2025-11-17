import asyncio
import logging
import time
from telegram import Update
from telegram.ext import ContextTypes

from config import settings  # Pour l'option "links" par défaut
from core.json_manager import storage_manager, MONITORS_FILE

# On récupère le logger global
logger = logging.getLogger('TelegramBot')


async def _get_next_monitor_id(monitors_list: list) -> int:
    """
    Calcule l'ID unique suivant en se basant sur le max(id) actuel.
    """
    if not monitors_list:
        return 1
    # Trouve l'ID le plus élevé et ajoute 1
    max_id = max(item.get('id', 0) for item in monitors_list)
    return max_id + 1


async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ajoute une nouvelle surveillance de compte X vers un chat Telegram.
    Format: /add_watch <@compte_x> <chat_id>
    """
    user = update.effective_user
    logger.info(f"Commande /add_watch reçue de {user.username} ({user.id})")

    # --- TODO: Ajouter la vérification de la whitelist ici ---
    # Pour l'instant, on laisse passer

    # 1. Valider les arguments
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /add_watch <@compte_x> <chat_id>\n"
            "Exemple: /add_watch @elonmusk -100123456789"
        )
        return

    x_account = context.args[0].replace('@', '').strip()
    telegram_chat_id = context.args[1].strip()

    # 2. Lire la base de données JSON
    monitors_data = await storage_manager.read_data(MONITORS_FILE)

    # 3. Vérifier les doublons
    for monitor in monitors_data:
        if (monitor.get('x_account') == x_account and
                monitor.get('telegram_chat_id') == telegram_chat_id):
            await update.message.reply_text(f"⚠️ Cette surveillance (@{x_account} -> {telegram_chat_id}) existe déjà.")
            return

    # 4. Générer le nouvel objet Monitor (avec ID unique)
    new_id = await _get_next_monitor_id(monitors_data)

    new_monitor = {
        "id": new_id,
        "x_account": x_account,
        "telegram_chat_id": telegram_chat_id,
        "include_links": settings.INCLUDE_LINKS_DEFAULT,
        "enabled": True,
        "last_post_id": "INIT",
        # Signifie "Run initial, prendre 1 seul tweet"
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    # 5. Ajouter et sauvegarder
    monitors_data.append(new_monitor)
    await storage_manager.write_data(MONITORS_FILE, monitors_data)

    logger.info(f"Nouvelle surveillance (ID: {new_id}) ajoutée par {user.username}")
    await update.message.reply_text(
        f"✅ Surveillance ajoutée !\n"
        f"ID: {new_id}\n"
        f"Compte X: @{x_account}\n"
        f"Chat Telegram: {telegram_chat_id}"
    )