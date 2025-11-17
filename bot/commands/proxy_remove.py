import logging
from telegram import Update
from telegram.ext import ContextTypes

from core.json_manager import storage_manager, PROXIES_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')

@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Supprime un proxy par son ID.
    Usage: /proxy_remove <ID_du_proxy>
    """
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /proxy_remove <ID_du_proxy> (Utilisez /proxy_list pour l'ID)")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        # Correction de l'encodage (était: Ôøö L'ID doit ├¬tre un nombre entier.)
        await update.message.reply_text("⛔ L'ID doit être un nombre entier.")
        return

    # 1. Lire les données
    proxies = await storage_manager.read_data(PROXIES_FILE)

    # 2. Trouver et filtrer le proxy à supprimer
    initial_count = len(proxies)

    # Nouvelle liste SANS l'ID ciblé
    new_proxies = [p for p in proxies if p.get('id') != target_id]

    # 3. Vérifier le résultat
    if len(new_proxies) == initial_count:
        # Correction de l'encodage
        await update.message.reply_text(f"⚠️ Proxy ID `{target_id}` non trouvé.")
        return

    # 4. Sauvegarder la nouvelle liste
    await storage_manager.write_data(PROXIES_FILE, new_proxies)

    logger.info(f"Proxy ID {target_id} retiré par {update.effective_user.username}")
    # Correction de l'encodage
    await update.message.reply_text(f"🗑️ Proxy ID **`{target_id}`** retiré de la liste.")