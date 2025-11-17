import logging
from telegram import Update
from telegram.ext import ContextTypes
from core.json_manager import storage_manager, MONITORS_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')

async def set_monitor_status(update: Update, context: ContextTypes.DEFAULT_TYPE, should_enable: bool):
    """
    Fonction utilitaire pour démarrer ou arrêter un moniteur.
    """
    action = "démarrer" if should_enable else "arrêter"

    if not context.args or len(context.args) != 1:
        await update.message.reply_text(f"Usage: /{action}_monitor <ID_du_moniteur> (Voir /list_watches)")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        # Correction de l'encodage
        await update.message.reply_text("⛔ L'ID doit être un nombre entier.")
        return

    monitors = await storage_manager.read_data(MONITORS_FILE)
    found = False

    for m in monitors:
        if m.get('id') == target_id:
            if m.get('enabled') == should_enable:
                # Si l'état est déjà le bon
                status_text = "déjà actif" if should_enable else "déjà inactif"
                # Correction de l'encodage
                await update.message.reply_text(f"⚠️ Le moniteur ID `{target_id}` est {status_text}.")
                return

            # Modifier l'état
            m['enabled'] = should_enable
            found = True
            break

    if not found:
        await update.message.reply_text(f"⚠️ Moniteur ID `{target_id}` non trouvé.")
        return

    # Sauvegarder et informer
    await storage_manager.write_data(MONITORS_FILE, monitors)
    status_text = "Activé (Démarrera au prochain cycle)" if should_enable else "Désactivé"
    logger.info(f"Moniteur ID {target_id} {action} par {update.effective_user.username}")
    await update.message.reply_text(f"✅ Moniteur ID **`{target_id}`** {status_text}.")


@whitelist_required
async def start_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Démarre une surveillance."""
    await set_monitor_status(update, context, True)


@whitelist_required
async def stop_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Arrête une surveillance."""
    await set_monitor_status(update, context, False)