import asyncio
import random
import logging
from playwright.async_api import async_playwright
from typing import List, Dict

from config import settings
from core.json_manager import storage_manager, MONITORS_FILE
from .worker import run_worker  # On importera notre futur worker

# On récupère le logger global
logger = logging.getLogger('TelegramBot')

# La file d'attente partagée entre le manager et les workers
# maxsize=100 pour éviter qu'elle ne grandisse indéfiniment si les workers sont lents
task_queue = asyncio.Queue(maxsize=100)


async def producer_loop(stop_event: asyncio.Event):
    """
    Le "Producteur". Tourne en boucle pour alimenter la file d'attente.
    """
    logger.info("[Producer] Démarré.")
    while not stop_event.is_set():
        try:
            logger.info("[Producer] Cycle de récupération des tâches...")

            # 1. Récupérer les monitors actifs depuis le JSON
            # On utilise notre manager sécurisé
            monitors_data = await storage_manager.read_data(MONITORS_FILE)
            active_monitors = [m for m in monitors_data if m.get('enabled', True)]

            if not active_monitors:
                logger.info("[Producer] Aucun monitor actif. En attente...")
            else:
                logger.info(f"[Producer] {len(active_monitors)} monitor(s) actif(s) à mettre en file d'attente.")

                # 2. Mélanger et ajouter à la file
                random.shuffle(active_monitors)  # Pour varier l'ordre

                for monitor_task in active_monitors:
                    if task_queue.full():
                        logger.warning("[Producer] La file d'attente est pleine. Pause de l'ajout.")
                        break  # On arrête d'ajouter pour ce cycle

                    # On ajoute le dictionnaire complet du monitor dans la file
                    await task_queue.put(monitor_task)

            # 3. Attendre aléatoirement entre 3 et 6 minutes
            wait_time = random.uniform(settings.MIN_WAIT_SECONDS, settings.MAX_WAIT_SECONDS)
            logger.info(f"[Producer] Cycle terminé. Prochain cycle dans {wait_time:.0f} secondes.")

            # On utilise wait_for pour que l'attente soit interruptible par le stop_event
            await asyncio.wait_for(stop_event.wait(), timeout=wait_time)

        except asyncio.TimeoutError:
            continue  # C'est normal, le timeout de wait_for est atteint, on boucle
        except asyncio.CancelledError:
            logger.info("[Producer] Tâche annulée.")
            break
        except Exception as e:
            logger.exception(f"[Producer] Erreur critique: {e}")
            await asyncio.sleep(60)  # Pause de 60s avant de réessayer


async def start_scheduler(app):
    """
    Point d'entrée du scheduler.
    Démarre Playwright, le Producer et les Workers.
    """
    stop_event = asyncio.Event()
    worker_tasks = []

    try:
        async with async_playwright() as p:
            logger.info("Playwright démarré en mode async.")

            # On passe l'instance 'p' de Playwright et 'app' (le bot) aux workers
            worker_context = {
                "playwright": p,
                "bot_app": app
            }

            # 1. Lancer les 4 Workers (Consommateurs)
            logger.info(f"Lancement de {settings.WORKER_COUNT} worker(s)...")
            for i in range(settings.WORKER_COUNT):
                task = asyncio.create_task(run_worker(
                    worker_id=i,
                    task_queue=task_queue,
                    stop_event=stop_event,
                    context=worker_context
                ))
                worker_tasks.append(task)

            # 2. Lancer le Manager (Producteur)
            producer_task = asyncio.create_task(producer_loop(stop_event))

            # 3. Attendre que tout se termine (normalement jamais)
            await producer_task

    except asyncio.CancelledError:
        logger.info("[SchedulerManager] Signal d'arrêt reçu.")
    except Exception as e:
        logger.exception(f"[SchedulerManager] Erreur fatale: {e}")
    finally:
        logger.info("[SchedulerManager] Arrêt des workers et du producer...")
        stop_event.set()  # Dit à toutes les tâches de s'arrêter

        # Attend que les workers finissent proprement
        await asyncio.gather(*worker_tasks, return_exceptions=True)
        logger.info("[SchedulerManager] Tous les workers sont arrêtés.")