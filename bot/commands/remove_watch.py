import logging
from telegram import Update
from telegram.ext import ContextTypes
from core.json_manager import storage_manager, MONITORS_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Supprime une surveillance par son ID.
    Usage: /remove_watch <ID_du_moniteur>
    """
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /remove_watch <ID_du_moniteur> (Utilisez /list_watches pour l'ID)")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⛔ L'ID doit être un nombre entier.")
        return

    # 1. Lire les moniteurs
    monitors = await storage_manager.read_data(MONITORS_FILE)

    # 2. Trouver et filtrer le moniteur à supprimer
    initial_count = len(monitors)

    # Nouvelle liste SANS l'ID ciblé
    new_monitors = [m for m in monitors if m.get('id') != target_id]

    # 3. Vérifier le résultat
    if len(new_monitors) == initial_count:
        await update.message.reply_text(f"⚠️ Surveillance ID `{target_id}` non trouvée.")
        return

    # 4. Sauvegarder la nouvelle liste
    await storage_manager.write_data(MONITORS_FILE, new_monitors)

    logger.info(f"Surveillance ID {target_id} supprimée par {update.effective_user.username}")
    # Note: On utilise monitors[0] uniquement pour le log, car nous n'avons pas le nom du compte à afficher
    # Cependant, si la liste monitors est vide, cela causera une erreur.
    # Pour l'affichage, il est plus sûr d'afficher uniquement l'ID.
    await update.message.reply_text(
        f"🗑️ Surveillance ID **`{target_id}`** retirée de la liste."
    )