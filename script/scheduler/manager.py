import asyncio
import random
import logging
from playwright.async_api import async_playwright
from typing import List, Dict
from telegram.ext import Application
import time

from config import settings
from core.json_manager import storage_manager, MONITORS_FILE
from script.scheduler.worker import run_worker

# On récupère le logger global
logger = logging.getLogger('TelegramBot')

# La file d'attente partagée entre le manager et les workers
task_queue = asyncio.Queue(maxsize=100)

# Clés utilisées pour le statut dans bot_data (pour /worker_status)
SCHEDULER_KEY = 'scheduler_status'
WORKERS_KEY = 'worker_tasks'

# --- Liste des chemins des 5 profils ---
# (Assurez-vous que ces profils existent et ont une session X valide)
PROFILE_PATHS = [
    "/app/my_playwright_profile_1",
    "/app/my_playwright_profile_2",
    "/app/my_playwright_profile_3",
    "/app/my_playwright_profile_4",
    "/app/my_playwright_profile_5",

]


# -----------------------------------------------

async def producer_loop(app: Application, stop_event: asyncio.Event):
    """
    Le "Producteur". Tourne en boucle pour alimenter la file d'attente
    et mettre à jour le statut du scheduler.
    """
    logger.info("[Producer] Démarré.")
    while not stop_event.is_set():
        try:
            logger.info("[Producer] Cycle de récupération des tâches...")

            # 1. Récupérer les monitors actifs depuis le JSON
            monitors_data = await storage_manager.read_data(MONITORS_FILE)
            active_monitors = [m for m in monitors_data if m.get('enabled', True)]

            # --- Mise à jour du statut avant d'attendre ---
            app.bot_data[SCHEDULER_KEY] = {
                'running': True,
                'last_run': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                'queue_size': task_queue.qsize(),
                'interval_sec': settings.MAX_WAIT_SECONDS,
            }
            # ----------------------------------------------

            if not active_monitors:
                # C'EST PROBABLEMENT VOTRE PROBLÈME :
                # S'il n'y a pas de moniteurs, il ne met rien dans la file
                # et passe directement à l'attente (wait_time).
                logger.info("[Producer] Aucun monitor actif. En attente...")
            else:
                logger.info(f"[Producer] {len(active_monitors)} monitor(s) actif(s) à mettre en file d'attente.")

                # 2. Mélanger et ajouter à la file
                random.shuffle(active_monitors)

                for monitor_task in active_monitors:
                    if task_queue.full():
                        logger.warning("[Producer] La file d'attente est pleine. Pause de l'ajout.")
                        break
                    # Le worker recevra la tâche ici
                    await task_queue.put(monitor_task)

            # 3. Attendre l'intervalle
            # C'EST L'AUTRE PROBLÈME POSSIBLE :
            # Si MIN_WAIT_SECONDS est 600, il attend 10 minutes ici.
            wait_time = random.uniform(settings.MIN_WAIT_SECONDS, settings.MAX_WAIT_SECONDS)
            logger.info(f"[Producer] Cycle terminé. Prochain cycle dans {wait_time:.0f} secondes.")

            # Attend 'wait_time' secondes ou jusqu'à ce que stop_event soit déclenché
            await asyncio.wait_for(stop_event.wait(), timeout=wait_time)

        except asyncio.TimeoutError:
            continue  # C'est le comportement normal, l'attente est terminée
        except asyncio.CancelledError:
            logger.info("[Producer] Tâche annulée.")
            break
        except Exception as e:
            logger.exception(f"[Producer] Erreur critique: {e}")
            app.bot_data[SCHEDULER_KEY]['running'] = False  # Indique l'échec
            await asyncio.sleep(60)  # Pause avant de réessayer en cas d'erreur grave


async def start_scheduler(app: Application):
    """
    Point d'entrée du scheduler.
    Démarre Playwright, le Producer et les Workers.
    """
    # Initialize le statut à Not Running
    app.bot_data[SCHEDULER_KEY] = {'running': False, 'last_run': 'Jamais', 'queue_size': 0,
                                   'interval_sec': settings.MAX_WAIT_SECONDS}

    stop_event = asyncio.Event()
    worker_tasks = []

    try:
        logger.info("Démarrage de Playwright en mode async...")

        # Vérification et ajustement de WORKER_COUNT pour ne pas dépasser le nombre de profils disponibles
        num_workers = min(settings.WORKER_COUNT, len(PROFILE_PATHS))

        if num_workers < settings.WORKER_COUNT:
            logger.warning(
                f"WORKER_COUNT ({settings.WORKER_COUNT}) est supérieur au nombre de profils ({len(PROFILE_PATHS)}). Utilisation de {num_workers} workers.")

        async with async_playwright() as p:
            logger.info("Playwright démarré avec succès.")
            worker_context_base = {
                "playwright": p,
                "bot_app": app
            }

            # 1. Lancer les Workers (Consommateurs)
            logger.info(f"Lancement de {num_workers} worker(s) avec des sessions dédiées...")
            for i in range(num_workers):
                profile_path = PROFILE_PATHS[i]  # Utilise un chemin de profil unique

                worker_context = worker_context_base.copy()
                # --- PASSAGE DU CHEMIN DE PROFIL UNIQUE ---
                worker_context["profile_path"] = profile_path
                # ------------------------------------------

                task = asyncio.create_task(run_worker(
                    worker_id=i + 1,
                    task_queue=task_queue,
                    stop_event=stop_event,
                    context=worker_context
                ))
                worker_tasks.append(task)

            # Stocker les tâches dans bot_data pour /worker_status
            app.bot_data[WORKERS_KEY] = worker_tasks

            # 2. Lancer le Manager (Producteur)
            producer_task = asyncio.create_task(producer_loop(app, stop_event))

            # 3. Attendre que tout se termine (normalement jamais, sauf si erreur)
            await producer_task

    except asyncio.CancelledError:
        logger.info("[SchedulerManager] Signal d'arrêt reçu.")
    except Exception as e:
        logger.exception(f"[SchedulerManager] Erreur fatale lors du démarrage de Playwright ou du Producer: {e}")
    finally:
        logger.info("[SchedulerManager] Arrêt des services...")
        stop_event.set()

        # Nettoyer l'état du Scheduler
        if SCHEDULER_KEY in app.bot_data:
            app.bot_data[SCHEDULER_KEY]['running'] = False
            app.bot_data[SCHEDULER_KEY]['queue_size'] = 0

        # Attend que les workers finissent proprement
        if worker_tasks:
            logger.info(f"Attente de la fin des {len(worker_tasks)} workers...")
            await asyncio.gather(*worker_tasks, return_exceptions=True)
            logger.info("[SchedulerManager] Tous les workers sont arrêtés.")