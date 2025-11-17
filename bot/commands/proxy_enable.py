import logging
from telegram import Update
from telegram.ext import ContextTypes
from core.json_manager import storage_manager, PROXIES_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')

# Constante pour réinitialiser le compteur d'erreurs
NEW_ERROR_COUNT = 0


async def _set_proxy_status(proxy_id: int, status: bool) -> (bool, str):
    """
    Met à jour l'état (actif/inactif) d'un proxy et réinitialise les erreurs.
    Retourne (succès, message_détail).
    """
    proxies = await storage_manager.read_data(PROXIES_FILE)

    proxy_index = next((i for i, p in enumerate(proxies) if p['id'] == proxy_id), None)

    if proxy_index is None:
        return False, f"Proxy ID {proxy_id} non trouvé."

    # Mise à jour de l'état
    proxies[proxy_index]['active'] = status
    proxies[proxy_index]['error_count'] = NEW_ERROR_COUNT

    await storage_manager.write_data(PROXIES_FILE, proxies)

    proxy_url_display = proxies[proxy_index]['proxy_url'][:30] + "..."
    return True, f"Proxy `{proxy_url_display}` réactivé avec succès. Compteur d'erreurs réinitialisé."


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Réactive un proxy désactivé par le système et réinitialise son compteur d'erreurs.
    Usage: /proxy_enable <ID_du_proxy>
    """
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /proxy_enable <ID_du_proxy> (Utilisez /proxy_list pour l'ID)")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⛔ L'ID doit être un nombre entier.")
        return

    success, message = await _set_proxy_status(target_id, status=True)

    if success:
        logger.info(f"Proxy ID {target_id} réactivé par {update.effective_user.username}")
        await update.message.reply_text(f"✅ Opération réussie!\n{message}")
    else:
        await update.message.reply_text(f"⚠️ Échec de la réactivation: {message}")