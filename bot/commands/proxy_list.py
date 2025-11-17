import logging
from telegram import Update
from telegram.ext import ContextTypes
from core.json_manager import storage_manager, PROXIES_FILE
from core.auth import whitelist_required
# On importe la fonction helper pour gérer les messages longs (définie dans list_watches.py/status.py)
from .list_watches import send_long_message # Assurez-vous que list_watches.py existe et contient send_long_message

logger = logging.getLogger('TelegramBot')


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Affiche la liste de tous les proxies enregistrés avec leur statut d'activité et d'erreur.
    """
    logger.info(f"Commande /proxy_list reçue de {update.effective_user.username}.")

    try:
        proxies = await storage_manager.read_data(PROXIES_FILE)
    except Exception as e:
        await update.message.reply_text(f"⛔ Erreur lors de la lecture des proxies: {e}")
        return

    if not proxies:
        await update.message.reply_text("🔎 Aucun proxy n'est enregistré.")
        return

    # Construire le message de réponse
    response_parts = ["📡 **Liste des Proxies Enregistrés**\n"]

    for p in proxies:
        # Déterminer le statut et la couleur
        status = "✅ ACTIF" if p.get('active') else "❌ INACTIF"
        errors = p.get('error_count', 0)

        # Affichage (tronqué pour ne pas exposer le mot de passe dans le log Telegram)
        url_display = p['proxy_url']
        if len(url_display) > 50:
            url_display = url_display[:30] + "..." + url_display[-10:]

        entry = (
            f"--- Proxy ID: `{p['id']}` ---\n"
            f"Statut: **{status}**\n"
            f"URL: `{url_display}`\n"
            f"Erreurs: {errors} 🚫 | Dernière utilisation: {p.get('last_used', 'N/A').split('T')[0]}\n"
        )
        response_parts.append(entry)

    final_message = "\n".join(response_parts)

    # Utilisation de la fonction helper
    await send_long_message(
        update,
        final_message,
        parse_mode='Markdown'
    )