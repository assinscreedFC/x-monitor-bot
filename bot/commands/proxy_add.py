import logging
from telegram import Update
from telegram.ext import ContextTypes
import time
import re

from core.json_manager import storage_manager, PROXIES_FILE
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')

# Regex pour valider un format de proxy de base (http://ip:port ou http://user:pass@ip:port)
PROXY_REGEX = re.compile(
    r'^(http|https|socks5):\/\/([^:]+:[^@]+@)?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|[a-zA-Z0-9\-\.]+):(\d{1,5})$')


async def _get_next_proxy_id(proxies_list: list) -> int:
    """Calcule l'ID unique suivant pour un proxy."""
    if not proxies_list:
        return 1
    # Trouve l'ID le plus élevé et ajoute 1
    max_id = max(item.get('id', 0) for item in proxies_list)
    return max_id + 1


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ajoute une URL de proxy à la liste de rotation.
    Usage: /proxy_add <http://user:pass@ip:port>
    """
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /proxy_add <http://user:pass@ip:port>")
        return

    proxy_url = context.args[0].strip()

    if not PROXY_REGEX.match(proxy_url):
        await update.message.reply_text(
            "⛔ Format de proxy invalide. Utilisez le format 'http://ip:port' ou 'http://user:pass@ip:port'.")
        return

    # 1. Lire la base de données JSON
    proxies_data = await storage_manager.read_data(PROXIES_FILE)

    # 2. Vérifier les doublons d'URL
    if any(p.get('proxy_url') == proxy_url for p in proxies_data):
        await update.message.reply_text(f"⚠️ Cette URL de proxy existe déjà.")
        return

    # 3. Générer le nouvel objet Proxy (avec ID unique)
    new_id = await _get_next_proxy_id(proxies_data)

    new_proxy = {
        "id": new_id,
        "proxy_url": proxy_url,
        "active": True,
        "error_count": 0,
        "last_used": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    # 4. Ajouter et sauvegarder
    proxies_data.append(new_proxy)
    await storage_manager.write_data(PROXIES_FILE, proxies_data)

    logger.info(f"Proxy ID {new_id} ajouté par {update.effective_user.username}")
    await update.message.reply_text(
        f"✅ Proxy ajouté (ID: **`{new_id}`**).\n"
        f"URL: `{proxy_url[:30]}...`\n"
        f"Statut: Actif."
    )