import asyncio
import logging
from asyncio import Queue
from telegram.ext import Application
from telegram.constants import ParseMode
from telegram.error import TelegramError

from config import settings
from core.json_manager import storage_manager, MONITORS_FILE

# from script.scrapers.twitter import fetch_new_posts  # Import retiré temporairement
# TODO: Rétablir l'import de fetch_new_posts une fois le fichier scraper reconstruit

# On récupère le logger global
logger = logging.getLogger('TelegramBot')

# Le chemin du profil Playwright à l'intérieur du conteneur Docker
# (doit correspondre au volume dans docker-compose.yml)
DOCKER_PROFILE_PATH = "/app/my_playwright_profile"


async def send_telegram_message(app: Application, chat_id: str, text: str, include_links: bool):
    """
    Fonction utilitaire pour envoyer un message via le bot,
    avec gestion des erreurs.
    """
    try:
        # Construit le message final
        message = text

        # TODO: Implémenter la logique de suppression de liens si nécessaire
        # if not include_links:
        #     import re
        #     message = re.sub(r'http[s]?://\S+', '', message)

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
        if "bot was blocked" in str(e) or "chat not found" in str(e):
            logger.warning(f"Désactivation du monitor pour {chat_id} (bot bloqué/chat non trouvé)")
            await set_monitor_enabled_status(chat_id, False)
        return False
    except Exception as e:
        logger.exception(f"Erreur inattendue lors de l'envoi du message: {e}")
        return False


async def update_last_post_id_in_json(monitor_id: int, new_last_post_id: str):
    """
    Met à jour le 'last_post_id' pour un monitor spécifique dans monitors.json.
    Opération atomique grâce au storage_manager.
    (new_last_post_id contient maintenant la date ISO pour le suivi temporel)
    """
    logger.info(f"Mise à jour de last_post_id={new_last_post_id} pour monitor ID {monitor_id}")

    monitors_data = await storage_manager.read_data(MONITORS_FILE)

    monitor_found = False
    for monitor in monitors_data:
        # On utilise l'ID du monitor (plus fiable)
        if monitor.get('id') == monitor_id:
            monitor['last_post_id'] = new_last_post_id
            monitor_found = True
            break

    if monitor_found:
        await storage_manager.write_data(MONITORS_FILE, monitors_data)
    else:
        logger.warning(f"Impossible de mettre à jour last_post_id: monitor ID {monitor_id} non trouvé.")


async def set_monitor_enabled_status(chat_id: str, enabled: bool):
    """Désactive tous les monitors liés à un chat_id (ex: bot bloqué)."""
    monitors_data = await storage_manager.read_data(MONITORS_FILE)
    modified = False
    for monitor in monitors_data:
        if monitor.get('telegram_chat_id') == chat_id:
            monitor['enabled'] = enabled
            modified = True

    if modified:
        await storage_manager.write_data(MONITORS_FILE, monitors_data)


async def run_worker(worker_id: int, task_queue: Queue, stop_event: asyncio.Event, context: dict):
    """
    La fonction principale du Worker (Consommateur).
    Attend une tâche et la traite.
    """
    logger.info(f"[Worker {worker_id}] Démarré et en attente de tâches.")

    # Récupère les objets Playwright et Bot depuis le contexte
    p = context["playwright"]
    app = context["bot_app"]

    # TODO: Logique de rotation des proxies
    # next_proxy = await get_next_available_proxy()
    # proxy_config = {'server': next_proxy['proxy_url']} if next_proxy else None

    proxy_config = None  # Placeholder

    while not stop_event.is_set():
        try:
            # 1. Attendre une tâche de la file d'attente
            monitor_task = await task_queue.get()

            logger.info(f"[Worker {worker_id}] Tâche reçue: Scraper @{monitor_task.get('x_account')}")

            # 2. Extraire les infos de la tâche
            account = monitor_task.get('x_account')
            chat_id = monitor_task.get('telegram_chat_id')
            last_seen_id = monitor_task.get('last_post_id')
            monitor_id = monitor_task.get('id')
            include_links = monitor_task.get('include_links', True)

            if not all([account, chat_id, monitor_id]):
                logger.error(f"[Worker {worker_id}] Tâche invalide (infos manquantes): {monitor_task}")
                task_queue.task_done()
                continue

            # 3. Exécuter le scraping (la grosse tâche I/O)
            # NOTE: L'import de fetch_new_posts doit être rétabli
            # new_tweets = await fetch_new_posts(
            #     p=p,
            #     username=account,
            #     profile_path=DOCKER_PROFILE_PATH,
            #     last_seen_id=last_seen_id,
            #     proxy=proxy_config
            # )

            new_tweets = []  # Placeholder temporaire

            # 4. Traiter les résultats
            if not new_tweets:
                logger.info(f"[Worker {worker_id}] Pas de nouveaux tweets pour @{account}.")

                # Si c'était un run "INIT" et qu'on n'a rien trouvé, on le met à jour pour éviter le next INIT
                if last_seen_id == "INIT":
                    logger.info(
                        f"[Worker {worker_id}] Run initial pour @{account} terminé. Aucun tweet trouvé. Mise à jour.")
                    await update_last_post_id_in_json(monitor_id, None)
            else:
                logger.info(f"[Worker {worker_id}] {len(new_tweets)} nouveau(x) tweet(s) à envoyer pour @{account}!")

                new_last_id = last_seen_id
                for tweet in new_tweets:
                    # Formatage simple
                    message_text = f"<b>Nouveau post de @{account}:</b>\n\n"
                    message_text += f"{tweet['text']}\n\n"
                    message_text += f"<a href='{tweet['url']}'>Voir sur X</a>"

                    # Envoi du message
                    success = await send_telegram_message(app, chat_id, message_text, include_links)

                    if success:
                        # ✅ Mémorise le dernier ID envoyé (la date ISO)
                        new_last_id = tweet['date_str']
                    else:
                        logger.error(f"Échec envoi. Arrêt de la rafale pour @{account}.")
                        break

                    await asyncio.sleep(1)  # Pause de 1 seconde pour éviter le flood

                # 5. Mettre à jour le JSON si nécessaire
                if new_last_id != last_seen_id:
                    await update_last_post_id_in_json(monitor_id, new_last_id)

            # 6. Marquer la tâche comme terminée
            task_queue.task_done()
            logger.info(f"[Worker {worker_id}] Tâche @{account} terminée. En attente...")

        except asyncio.CancelledError:
            logger.info(f"[Worker {worker_id}] Tâche annulée.")
            break
        except Exception as e:
            logger.exception(f"[Worker {worker_id}] Erreur inattendue: {e}")
            # En cas d'erreur, on marque quand même la tâche comme finie
            if 'monitor_task' in locals():
                task_queue.task_done()