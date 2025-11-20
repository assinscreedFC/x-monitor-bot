import asyncio
import logging
from asyncio import Queue
from telegram.ext import Application
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram import InputMediaPhoto, InputMediaVideo

from config import settings
from core.json_manager import storage_manager, MONITORS_FILE
from core.proxy_manager import get_next_available_proxy, handle_proxy_failure
from script.scrapers.twitter import fetch_new_posts

# On récupère le logger global
logger = logging.getLogger('TelegramBot')


# --- Fonctions utilitaires du Worker ---

async def send_tweet_to_telegram(app: Application, chat_id: str, tweet: dict, include_links: bool,
                                 include_media: bool) -> bool:
    """
    Envoie un tweet sur Telegram.
    - include_links : Ajoute le lien du tweet à la fin du texte.
    - include_media : Si False, force l'envoi en texte seul (ignore images/vidéos).
    """
    try:
        # Préparation du texte (Caption)
        text_content = tweet['text']
        if include_links:
            text_content += f"\n\n🔗 <a href='{tweet['url']}'>Voir sur X</a>"

        # Gestion de l'option "include_media"
        # Si l'utilisateur ne veut pas les médias, on vide la liste localement
        media_urls = tweet.get('media', []) if include_media else []

        # --- CAS 1 : Pas de média (ou désactivé) -> Message texte simple ---
        if not media_urls:
            await app.bot.send_message(
                chat_id=chat_id,
                text=text_content,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=not include_links
            )
            return True

        # --- CAS 2 : Un seul média -> Photo ou Vidéo ---
        if len(media_urls) == 1:
            url = media_urls[0]
            # Détection basique vidéo
            if any(ext in url for ext in ['.mp4', '.m3u8', 'video']):
                """await app.bot.send_video(
                    chat_id=chat_id,
                    video=url,
                    caption=text_content,
                    parse_mode=ParseMode.HTML
                )"""
                await app.bot.send_message(
                    chat_id=chat_id,
                    text=text_content,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=not include_links
                )
            else:
                await app.bot.send_photo(
                    chat_id=chat_id,
                    photo=url,
                    caption=text_content,
                    parse_mode=ParseMode.HTML
                )
            return True

        # --- CAS 3 : Plusieurs médias -> Album (MediaGroup) ---
        if len(media_urls) > 1:
            media_group = []

            for i, url in enumerate(media_urls):
                # Seul le premier média de l'album peut avoir la légende
                # Attention: Limite de caption Telegram = 1024 chars
                caption = text_content if i == 0 else None

                if any(ext in url for ext in ['.mp4', '.m3u8', 'video']):
                    media_group.append(InputMediaVideo(media=url, caption=caption, parse_mode=ParseMode.HTML))
                else:
                    media_group.append(InputMediaPhoto(media=url, caption=caption, parse_mode=ParseMode.HTML))

            await app.bot.send_media_group(chat_id=chat_id, media=media_group)
            return True

    except TelegramError as e:
        logger.error(f"Erreur Telegram tweet {tweet['id']} (chat {chat_id}): {e}")

        # --- FALLBACK : Si l'envoi média échoue, on tente d'envoyer le texte seul ---
        try:
            fallback_text = f"{text_content}\n\n⚠️ <i>(Images non chargées: {e})</i>"
            await app.bot.send_message(
                chat_id=chat_id,
                text=fallback_text,
                parse_mode=ParseMode.HTML
            )
            return True
        except Exception:
            return False

    except Exception as e:
        logger.exception(f"Erreur inattendue envoi Telegram: {e}")
        return False

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
            proxy_config = await get_next_available_proxy()
            if proxy_config:
                selected_proxy_id = proxy_config.pop('id')

            logger.info(
                f"[Worker {worker_id}] Tâche reçue: Scraper @{monitor_task.get('x_account')} (Proxy ID: {selected_proxy_id or 'None'})")

            # 3. Configuration des options
            account = monitor_task.get('x_account')
            chat_id = monitor_task.get('telegram_chat_id')
            last_seen_id = monitor_task.get('last_post_id')
            monitor_id = monitor_task.get('id')

            # --- NOUVELLES OPTIONS ---
            include_links = monitor_task.get('include_links', True)
            include_media = monitor_task.get('include_media', True)  # Afficher les médias ?
            filter_only_photos = monitor_task.get('filter_only_photos', False)  # Ignorer si pas de photo ?

            # --- APPEL DU SCRAPER ---
            new_tweets = await fetch_new_posts(
                p=p,
                username=account,
                profile_path=profile_path_for_worker,
                last_seen_id=last_seen_id,
                proxy=proxy_config
            )

            # 4. Traiter les résultats
            if not new_tweets:
                if last_seen_id == "INIT":
                    await update_last_post_id_in_json(monitor_id, None)
            else:
                new_last_id = last_seen_id

                for tweet in new_tweets:

                    # --- FILTRAGE : Only Photos ---
                    # Si "Uniquement Photos" est activé, on analyse les médias du tweet
                    if filter_only_photos:
                        media_list = tweet.get('media', [])
                        # Si aucun média -> On passe au tweet suivant
                        if not media_list:
                            logger.info(f"Tweet {tweet['id']} ignoré (Filtre Only Photos: Pas de média).")
                            new_last_id = tweet['date_str']  # On met à jour l'ID pour ne pas re-scanner ce tweet ignoré
                            continue

                        # Si média présent, est-ce une vidéo ?
                        # Si on veut "Que les photos", on doit décider si on accepte les vidéos.
                        # Généralement "Only Photos" exclut les vidéos.
                        has_video = any(m for m in media_list if '.mp4' in m or '.m3u8' in m or 'video' in m)
                        if has_video:
                            logger.info(f"Tweet {tweet['id']} ignoré (Filtre Only Photos: Contient une vidéo).")
                            new_last_id = tweet['date_str']
                            continue

                    # --- ENVOI ---
                    # On passe include_media à la fonction d'envoi
                    success = await send_tweet_to_telegram(app, chat_id, tweet, include_links, include_media)

                    if success:
                        new_last_id = tweet['date_str']
                    else:
                        logger.error(f"Échec envoi Telegram. Arrêt de la rafale pour @{account}.")
                        break

                    # Petite pause pour éviter le flood Telegram
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

            if selected_proxy_id:
                await handle_proxy_failure(selected_proxy_id)

            if monitor_task:
                task_queue.task_done()