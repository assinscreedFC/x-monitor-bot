import logging
import re
import time
from telegram import Update
from telegram.ext import ContextTypes

from core.json_manager import storage_manager, PROXIES_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')

# Regex pour valider le format IP:PORT ou DOMAIN:PORT (sans l'authentification)
PROXY_REGEX = re.compile(r"^(?:https?://)?([\w\.\-]+:\d{2,5})$", re.IGNORECASE)


async def _get_next_id():
    """Détermine le prochain ID unique pour un nouveau proxy."""
    data = await storage_manager.read_data(PROXIES_FILE)
    if not data:
        return 1
    return max(p.get('id', 0) for p in data) + 1


async def _add_proxy_to_json(proxy_url_clean: str):
    """Ajoute le proxy au fichier JSON avec les métadonnées initiales."""

    data = await storage_manager.read_data(PROXIES_FILE)
    new_id = await _get_next_id()

    new_proxy = {
        "id": new_id,
        "proxy_url": proxy_url_clean,  # Stocke ip:port ou http://ip:port (sans creds)
        "active": True,
        "error_count": 0,
        "last_used": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    data.append(new_proxy)
    await storage_manager.write_data(PROXIES_FILE, data)
    return new_id, proxy_url_clean


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ajoute un proxy à la liste de rotation.
    Usage: /proxy_add <ip:port> (l'authentification est gérée par le .env)
    """
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /proxy_add <ip:port> ou <http://ip:port>\n"
            "L'utilisateur et le mot de passe sont pris dans le fichier de configuration (.env)."
        )
        return

    raw_url = context.args[0].strip()

    # 1. Validation de l'URL pour s'assurer qu'elle ne contient pas l'authentification
    # et qu'elle est au format IP:PORT ou DOMAIN:PORT
    match = PROXY_REGEX.match(raw_url)

    if not match:
        await update.message.reply_text(
            "⛔ Format de proxy invalide. Utilisez le format `ip:port` ou `http://ip:port`."
            " N'incluez PAS l'utilisateur et le mot de passe ici (ils sont dans le .env)."
        )
        return

    # Extrait l'URL nettoyée (peut contenir le protocole ou juste l'IP:Port)
    proxy_url_clean = raw_url

    try:
        new_id, url_added = await _add_proxy_to_json(proxy_url_clean)

        await update.message.reply_text(
            f"✅ Proxy ajouté (ID: **{new_id}**).\n"
            f"Adresse : `{url_added}`\n"
            f"Authentification : Utilise `PROXY_AUTH_USERNAME` du fichier .env.",
            parse_mode='Markdown'
        )
        logger.info(f"Nouveau proxy ajouté (ID: {new_id}, URL: {url_added}) par {update.effective_user.username}")

    except Exception as e:
        logger.exception(f"Erreur lors de l'ajout du proxy: {e}")
        await update.message.reply_text(f"Une erreur interne est survenue lors de l'ajout du proxy.")