import logging
from telegram import Update
from telegram.ext import ContextTypes
import asyncio # Nécessaire pour la fonction send_long_message

from core.json_manager import storage_manager, MONITORS_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')

# Constante Telegram pour la limite de message
TELEGRAM_MAX_MESSAGE_LENGTH = 4096


async def send_long_message(update: Update, text: str, parse_mode: str = None):
    """
    Découpe et envoie un long message en plusieurs parties pour respecter la limite de Telegram.
    """
    if len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH:
        await update.message.reply_text(text, parse_mode=parse_mode)
        return

    # Découpage du message
    parts = []
    current_part = ""

    # Tentative de découper par lignes pour ne pas couper au milieu d'un moniteur
    lines = text.split('\n')

    for line in lines:
        # Si l'ajout de la ligne dépasse la limite, on envoie la partie actuelle
        if len(current_part) + len(line) + 1 > TELEGRAM_MAX_MESSAGE_LENGTH:
            parts.append(current_part.strip())
            current_part = line + '\n'  # Commence une nouvelle partie
        else:
            current_part += line + '\n'

    # Ajout de la dernière partie
    if current_part:
        parts.append(current_part.strip())

    # Envoi de chaque partie
    for i, part in enumerate(parts):
        header = ""
        if i > 0:
            header = f"**(Suite - Partie {i + 1}/{len(parts)})**\n"

        await update.message.reply_text(header + part, parse_mode=parse_mode)
        # Petite pause pour éviter le flood si la liste est très longue
        if len(parts) > 2:
            await asyncio.sleep(0.5)


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Affiche la liste de toutes les surveillances actives et inactives.
    """
    logger.info(f"Commande /list_watches reçue de {update.effective_user.username}.")

    try:
        monitors = await storage_manager.read_data(MONITORS_FILE)
    except Exception as e:
        await update.message.reply_text(f"⛔ Erreur lors de la lecture des moniteurs: {e}")
        return

    if not monitors:
        await update.message.reply_text("🔎 Aucune surveillance n'est enregistrée.")
        return

    # Construire le message de réponse
    response_parts = ["📌 **Liste des Surveillances Actives/Inactives**\n"]

    for m in monitors:
        status = "✅ ACTIF" if m.get('enabled') else "❌ INACTIF"
        links = "🔗 Oui" if m.get('include_links', True) else "🚫 Non"
        last_id = m.get('last_post_id', 'INIT')

        last_status = "Nouveau (INIT)"
        if last_id and last_id != "INIT":
            # Si c'est une date, on affiche la date de la DB
            last_status = f"Dernier post: {last_id.split('T')[0]}"

        entry = (
            f"\n--- Monitor ID: `{m['id']}` ---\n"
            f"Statut: {status}\n"
            f"Compte X: **@{m['x_account']}**\n"
            f"Chat Cible: `{m['telegram_chat_id']}`\n"
            f"Options: [Liens: {links}] | [{last_status}]\n"
        )
        response_parts.append(entry)

    final_message = "\n".join(response_parts)

    # Utilisation de la nouvelle fonction pour gérer le découpage
    await send_long_message(
        update,
        final_message,
        parse_mode='Markdown'
    )