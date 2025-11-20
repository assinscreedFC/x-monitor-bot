import asyncio
import logging
from asyncio import Queue
from telegram.ext import Application
from telegram.constants import ParseMode
from telegram.error import TelegramError

from config import settings
from core.json_manager import storage_manager, MONITORS_FILE
from core.proxy_manager import get_next_available_proxy, handle_proxy_failure
from script.scrapers.twitter import fetch_new_posts

# On récupère le logger global
logger = logging.getLogger('TelegramBot')


# Rétire le chemin statique, il sera passé par le contexte
# DOCKER_PROFILE_PATH = "/app/my_playwright_profile"


# --- Fonctions utilitaires du Worker ---
async def send_telegram_message(app: Application, chat_id: str, text: str, include_links: bool):
    """
    Fonction utilitaire pour envoyer un message via le bot, avec gestion des erreurs.
    """
    try:
        message = text
        await app.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=not include_links
        )
        return True
    except TelegramError as e:
        logger.error(f"Erreur Telegram en envoyant au chat {chat_id}: {e}")
        # Si le bot est bloqué ou le chat non trouvé, on désactive le monitor
        # ...
        return False
    except Exception as e:
        logger.exception(f"Erreur inattendue lors de l'envoi du message: {e}")
        return False


async def update_last_post_id_in_json(monitor_id: int, new_last_post_id: str):
    """Met à jour le 'last_post_id' pour un monitor spécifique."""
    logger.info(f"Mise à jour de last_post_id={new_last_post_id} pour monitor ID {monitor_id}")
    monitors_data = await storage_manager.read_data(MONITORS_FILE)
    monitor_found = False
    for monitor in monitors_data:
        if monitor.get('id') == monitor_id:
            monitor['last_post_id'] = new_last_post_id
            monitor_found = True
            break
    if monitor_found:
        await storage_manager.write_data(MONITORS_FILE, monitors_data)
    else:
        logger.warning(f"Impossible de mettre à jour last_post_id: monitor ID {monitor_id} non trouvé.")


async def set_monitor_enabled_status(chat_id: str, enabled: bool):
    """Désactive tous les monitors liés à un chat_id."""
    monitors_data = await storage_manager.read_data(MONITORS_FILE)
    modified = False
    for monitor in monitors_data:
        if monitor.get('telegram_chat_id') == chat_id:
            monitor['enabled'] = enabled
            modified = True
    if modified:
        await storage_manager.write_data(MONITORS_FILE, monitors_data)


# --- Fonction principale du Worker ---

async def run_worker(worker_id: int, task_queue: Queue, stop_event: asyncio.Event, context: dict):
    """
    La fonction principale du Worker (Consommateur) avec gestion des proxies.
    """
    logger.info(f"[Worker {worker_id}] Démarré et en attente de tâches.")

    p = context["playwright"]
    app = context["bot_app"]

    # --- RÉCUPÉRATION DU CHEMIN DE PROFIL DÉDIÉ ---
    profile_path_for_worker = context["profile_path"]
    logger.info(f"[Worker {worker_id}] Profil Playwright dédié: {profile_path_for_worker}")
    # -----------------------------------------------

    while not stop_event.is_set():
        # Variables locales pour la tâche
        selected_proxy_id = None
        proxy_config = None
        monitor_task = None

        try:
            # 1. Attendre une tâche de la file d'attente
            monitor_task = await task_queue.get()

            # 2. Tenter de récupérer un proxy disponible
            proxy_config = await get_next_available_proxy()  # proxy_config contient maintenant id, server, username, password
            if proxy_config:
                # L'ID est maintenant directement dans le dictionnaire proxy_config
                selected_proxy_id = proxy_config.pop('id')

            logger.info(
                f"[Worker {worker_id}] Tâche reçue: Scraper @{monitor_task.get('x_account')} (Proxy ID: {selected_proxy_id or 'None'})")

            # 3. Exécuter le scraping
            account = monitor_task.get('x_account')
            chat_id = monitor_task.get('telegram_chat_id')
            last_seen_id = monitor_task.get('last_post_id')
            monitor_id = monitor_task.get('id')
            include_links = monitor_task.get('include_links', True)

            # --- APPEL DU SCRAPER avec le chemin de profil DÉDIÉ ---
            new_tweets = await fetch_new_posts(
                p=p,
                username=account,
                # Utilise le chemin de profil attribué au Worker
                profile_path=profile_path_for_worker,
                last_seen_id=last_seen_id,
                proxy=proxy_config
            )
            # --- FIN APPEL DU SCRAPER ---

            # 4. Traiter les résultats (si succès du scraping)
            if not new_tweets:
                if last_seen_id == "INIT":
                    await update_last_post_id_in_json(monitor_id, None)
            else:
                new_last_id = last_seen_id
                for tweet in new_tweets:
                    #message_text = f"<b>Nouveau post de @{account}:</b>\n\n"
                    message_text = f"{tweet['text']}"
                    message_text += f"<a href='{tweet['url']}'>Voir sur X</a>"

                    success = await send_telegram_message(app, chat_id, message_text, include_links)

                    if success:
                        new_last_id = tweet['date_str']
                    else:
                        logger.error(f"Échec envoi Telegram. Arrêt de la rafale pour @{account}.")
                        break

                    await asyncio.sleep(1)

                if new_last_id != last_seen_id:
                    await update_last_post_id_in_json(monitor_id, new_last_id)

            # 5. Marquer la tâche comme terminée
            task_queue.task_done()
            logger.info(f"[Worker {worker_id}] Tâche @{account} terminée. En attente...")

        except asyncio.CancelledError:
            logger.info(f"[Worker {worker_id}] Tâche annulée.")
            break
        except Exception as e:
            logger.exception(f"[Worker {worker_id}] Erreur inattendue lors du scraping: {e}")

            # 6. GÉRER L'ÉCHEC DU PROXY
            if selected_proxy_id:
                await handle_proxy_failure(selected_proxy_id)

            if monitor_task:
                task_queue.task_done()