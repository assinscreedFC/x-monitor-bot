import logging
import time
from typing import Dict, Optional, List
from core.json_manager import storage_manager, PROXIES_FILE
from config import settings

logger = logging.getLogger('TelegramBot')

MAX_PROXY_ERRORS = 4


async def get_next_available_proxy() -> Optional[Dict]:
    """
    Sélectionne le proxy actif le moins récemment utilisé pour la rotation.
    Met à jour son champ 'last_used' et retourne le proxy COMPLET pour le worker
    au format {server, username, password, id}.
    """
    proxies = await storage_manager.read_data(PROXIES_FILE)
    if not proxies:
        return None

    active_proxies = [p for p in proxies if p.get('active', True)]

    if not active_proxies:
        logger.warning("Aucun proxy actif n'est disponible. Reversion au scraping sans proxy.")
        return None

    sorted_proxies = sorted(active_proxies, key=lambda p: p.get('last_used', '1970-01-01T00:00:00Z'))
    selected_proxy = sorted_proxies[0]

    proxy_ip_port = selected_proxy.get('proxy_url')

    # Sécurité : Vérifier que l'URL du proxy n'est pas vide
    if not proxy_ip_port:
        logger.error(f"Proxy ID {selected_proxy['id']} a une 'proxy_url' vide. Il sera ignoré pour ce tour.")
        # On pourrait aussi appeler handle_proxy_failure ici si on le souhaite
        return None  # Ne retourne rien, le worker n'utilisera pas de proxy

    if not proxy_ip_port.startswith('http'):
        proxy_ip_port = 'http://' + proxy_ip_port

    # 5. Préparer le dictionnaire de configuration du proxy au format désiré
    proxy_config_for_worker = {
        'server': proxy_ip_port,
        'username': settings.PROXY_AUTH_USERNAME,
        'password': settings.PROXY_AUTH_PASSWORD,
        'id': selected_proxy['id']  # On inclut l'ID pour le suivi dans le worker
    }

    # 6. Mettre à jour 'last_used' du proxy sélectionné dans le JSON
    new_last_used = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    proxy_index = next((i for i, p in enumerate(proxies) if p['id'] == selected_proxy['id']), None)

    if proxy_index is not None:
        proxies[proxy_index]['last_used'] = new_last_used
        await storage_manager.write_data(PROXIES_FILE, proxies)

        logger.debug(f"Proxy ID {selected_proxy['id']} sélectionné. Configuration proxy (server/user/pass) construite.")
        # --- LA CORRECTION EST ICI ---
        return proxy_config_for_worker  # On retourne le dictionnaire formaté

    return None

async def handle_proxy_failure(proxy_id: int):
    """
    Gère l'échec d'un proxy: incrémente son compteur d'erreurs et le désactive
    s'il atteint le seuil MAX_PROXY_ERRORS.
    """
    proxies = await storage_manager.read_data(PROXIES_FILE)

    proxy_index = next((i for i, p in enumerate(proxies) if p['id'] == proxy_id), None)

    if proxy_index is not None:
        proxy = proxies[proxy_index]
        current_errors = proxy.get('error_count', 0) + 1

        proxy['error_count'] = current_errors

        if current_errors >= MAX_PROXY_ERRORS:
            proxy['active'] = False
            logger.error(
                f"🛑 Proxy ID {proxy_id} désactivé! Erreurs atteintes: {current_errors}/{MAX_PROXY_ERRORS}"
            )
        else:
            logger.warning(
                f"⚠️ Échec du Proxy ID {proxy_id}. Compteur d'erreurs: {current_errors}/{MAX_PROXY_ERRORS}"
            )

        # Sauvegarder l'état mis à jour
        await storage_manager.write_data(PROXIES_FILE, proxies)
    else:
        logger.error(f"Tentative de gérer l'échec d'un Proxy ID non trouvé: {proxy_id}")