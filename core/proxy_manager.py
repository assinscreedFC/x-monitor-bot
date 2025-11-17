import logging
import time
from typing import Dict, Optional, List
from core.json_manager import storage_manager, PROXIES_FILE
from config import settings  # NOUVEL IMPORT CRITIQUE

logger = logging.getLogger('TelegramBot')

# Constante: Nombre maximal d'erreurs avant désactivation du proxy
MAX_PROXY_ERRORS = 5


async def get_next_available_proxy() -> Optional[Dict]:
    """
    Sélectionne le proxy actif le moins récemment utilisé pour la rotation.
    Met à jour son champ 'last_used' et retourne le proxy COMPLET pour le worker.
    """
    proxies = await storage_manager.read_data(PROXIES_FILE)
    if not proxies:
        return None

    # 1. Filtrer pour ne garder que les proxies ACTIFS
    active_proxies = [p for p in proxies if p.get('active', True)]

    if not active_proxies:
        logger.warning("Aucun proxy actif n'est disponible. Reversion au scraping sans proxy.")
        return None

    # 2. Trier par 'last_used' (le plus ancien en premier)
    sorted_proxies = sorted(active_proxies, key=lambda p: p.get('last_used', '1970-01-01T00:00:00Z'))

    # 3. Sélectionner le premier (le moins récemment utilisé)
    selected_proxy = sorted_proxies[0]

    # 4. Construire l'URL Playwright complète avec l'authentification centralisée
    proxy_ip_port = selected_proxy.get('proxy_url')
    username = settings.PROXY_AUTH_USERNAME
    password = settings.PROXY_AUTH_PASSWORD

    # Le proxy_url stocké est maintenant l'adresse IP et le port (ex: http://ip:port)
    if username and password:
        # Assurez-vous d'avoir le protocole (ex: http://) pour l'insertion des creds
        if not proxy_ip_port.startswith('http'):
            proxy_ip_port = 'http://' + proxy_ip_port

        # Insertion de l'authentification dans l'URL
        full_proxy_url = proxy_ip_port.replace('://', f'://{username}:{password}@')
    else:
        full_proxy_url = proxy_ip_port

    selected_proxy['proxy_url'] = full_proxy_url  # Mise à jour temporaire pour le worker

    # 5. Mettre à jour 'last_used' du proxy sélectionné dans le JSON (sans l'URL complète pour le stockage)
    new_last_used = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Trouver l'index du proxy dans la liste complète pour la sauvegarde
    proxy_index = next((i for i, p in enumerate(proxies) if p['id'] == selected_proxy['id']), None)

    if proxy_index is not None:
        proxies[proxy_index]['last_used'] = new_last_used
        # Sauvegarder la liste mise à jour
        await storage_manager.write_data(PROXIES_FILE, proxies)

        logger.debug(f"Proxy ID {selected_proxy['id']} sélectionné et mis à jour (last_used). URL complète construite.")
        return selected_proxy

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