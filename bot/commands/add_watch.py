import asyncio
import logging
import time
from telegram import Update
from telegram.ext import ContextTypes

from config import settings  # Pour l'option "links" par défaut
from core.json_manager import storage_manager, MONITORS_FILE
from core.auth import whitelist_required  # <-- IMPORT DE LA SÉCURITÉ

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


@whitelist_required  # <-- DÉCORATEUR AJOUTÉ
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ajoute une nouvelle surveillance de compte X vers un chat Telegram.
    Format: /add_watch <@compte_x> <chat_id> [inclure_liens: true/false]
    """
    user = update.effective_user
    logger.info(f"Commande /add_watch reçue de {user.username} ({user.id})")

    # 1. Valider les arguments
    # Doit avoir au moins 2 arguments (compte et chat_id)
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /add_watch <@compte_x> <chat_id> [inclure_liens: true/false]\n"
            "Exemple: /add_watch @NASA -100123456789 true"
        )
        return

    x_account = context.args[0].replace('@', '').strip()
    telegram_chat_id = context.args[1].strip()

    # 2. Gérer l'argument optionnel 'include_links'
    # Par défaut, utilise la valeur de settings.INCLUDE_LINKS_DEFAULT
    include_links_status = settings.INCLUDE_LINKS_DEFAULT

    if len(context.args) > 2:
        link_arg = context.args[2].lower()
        if link_arg in ['true', 'on', 'yes']:
            include_links_status = True
        elif link_arg in ['false', 'off', 'no']:
            include_links_status = False
        else:
            await update.message.reply_text(
                "⚠️ Argument 'inclure_liens' non valide. Utilisez 'true' ou 'false'."
            )
            return

    # 3. Lire la base de données JSON
    monitors_data = await storage_manager.read_data(MONITORS_FILE)

    # 4. Vérifier les doublons
    for monitor in monitors_data:
        if (monitor.get('x_account') == x_account and
                monitor.get('telegram_chat_id') == telegram_chat_id):
            await update.message.reply_text(f"⚠️ Cette surveillance (@{x_account} -> {telegram_chat_id}) existe déjà.")
            return

    # 5. Générer le nouvel objet Monitor (avec ID unique)
    new_id = await _get_next_monitor_id(monitors_data)

    new_monitor = {
        "id": new_id,
        "x_account": x_account,
        "telegram_chat_id": telegram_chat_id,
        "include_links": include_links_status,  # Utilise la valeur décidée
        "enabled": True,
        "last_post_id": "INIT",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    # 6. Ajouter et sauvegarder
    monitors_data.append(new_monitor)
    await storage_manager.write_data(MONITORS_FILE, monitors_data)

    logger.info(f"Nouvelle surveillance (ID: {new_id}) ajoutée par {user.username}")

    # Message de confirmation
    links_text = "Oui" if include_links_status else "Non"
    await update.message.reply_text(
        f"✅ Surveillance ajoutée !\n"
        f"ID: <b>{new_id}</b>\n"
        f"Compte X: <b>@{x_account}</b>\n"
        f"Chat Telegram: <b>{telegram_chat_id}</b>\n"
        f"Inclure les liens: <b>{links_text}</b>",
        parse_mode='HTML'
    )