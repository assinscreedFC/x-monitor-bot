import logging
import time
import os
from telegram import Update
from telegram.ext import ContextTypes
import asyncio

from core.json_manager import storage_manager, MONITORS_FILE, WHITELIST_FILE
from core.auth import whitelist_required
from config import settings

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

    parts = []
    current_part = ""
    lines = text.split('\n')

    for line in lines:
        if len(current_part) + len(line) + 1 > TELEGRAM_MAX_MESSAGE_LENGTH:
            parts.append(current_part.strip())
            current_part = line + '\n'
        else:
            current_part += line + '\n'

    if current_part:
        parts.append(current_part.strip())

    for i, part in enumerate(parts):
        header = ""
        if i > 0:
            header = f"**(Suite - Partie {i + 1}/{len(parts)})**\n"

        await update.message.reply_text(header + part, parse_mode=parse_mode)
        if len(parts) > 2:
            await asyncio.sleep(0.5)

@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Affiche un aperçu du statut du bot (nombre de moniteurs, utilisateurs, etc.).
    """
    # Correction des encodages des emojis
    response_parts = ["✨ **Statut du Système Bot** ✨\n"]

    try:
        # 1. Moniteurs
        monitors = await storage_manager.read_data(MONITORS_FILE)
        active_monitors = sum(1 for m in monitors if m.get('enabled', False))
        inactive_monitors = len(monitors) - active_monitors

        response_parts.append(f"📡 **Surveillances Totales :** {len(monitors)}")
        response_parts.append(f"   • Actives : {active_monitors} ✅")
        response_parts.append(f"   • Inactives : {inactive_monitors} ❌")

        # 2. Whitelist
        whitelist = await storage_manager.read_data(WHITELIST_FILE)
        response_parts.append(f"\n👤 **Administrateurs Whitelistés :** {len(whitelist)}")

        # 3. Dernier check (basé sur la modification du fichier)
        response_parts.append("\nℹ️ **Infos DB :**")

        monitors_path = os.path.join(settings.STORAGE_DIR, MONITORS_FILE)
        # Vérifiez que le chemin d'accès au fichier est correct et que le fichier existe
        if os.path.exists(monitors_path):
            last_monitor_mod = time.ctime(os.path.getmtime(monitors_path))
            response_parts.append(f"   • Dernière modif moniteurs: {last_monitor_mod}")
        else:
            response_parts.append("   • Fichier moniteurs non trouvé.")

    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {e}")
        response_parts.append(f"🛑 **Erreur Système :** Problème de lecture des fichiers.")

    final_message = "\n".join(response_parts)

    # Utilisation de la nouvelle fonction pour gérer le découpage
    await send_long_message(
        update,
        final_message,
        parse_mode='Markdown')