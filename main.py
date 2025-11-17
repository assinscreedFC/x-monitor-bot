import asyncio
import logging
import signal
import sys

# Importe notre config d'abord pour initialiser le logging
from config import settings

# Importe nos modules principaux
from bot.main import setup_bot
from script.scheduler.manager import start_scheduler
from core.json_manager import storage_manager  # On importe notre manager JSON

# Récupère le logger
logger = logging.getLogger('TelegramBot')


async def main():
    """
    Point d'entrée principal (Chef d'Orchestre).
    Initialise, démarre et gère le bot et le scheduler.
    """
    logger.info("Démarrage du chef d'orchestre...")

    # 1. Prépare l'application bot (sans la lancer)
    bot_app = setup_bot()

    # Tâches à exécuter en parallèle
    scheduler_task = None

    try:
        # 2. Initialise l'application bot (prépare la connexion)
        await bot_app.initialize()

        # 3. Lance le "polling" (réception des messages)
        # c'est non-bloquant et tourne en arrière-plan
        await bot_app.updater.start_polling()

        # 4. Démarre l'application bot (active les handlers)
        await bot_app.start()
        logger.info("Bot Telegram démarré et en polling.")

        # 5. Démarre notre scheduler/worker manager
        scheduler_task = asyncio.create_task(start_scheduler(bot_app))

        # 6. Attend que la tâche du scheduler se termine (normalement jamais)
        await scheduler_task

    except (KeyboardInterrupt, SystemExit):
        logger.info("Signal d'arrêt reçu (Ctrl+C).")
    except Exception as e:
        logger.exception(f"Erreur critique dans le main: {e}")
    finally:
        logger.info("Arrêt des services...")

        # Arrête le scheduler proprement
        if scheduler_task and not scheduler_task.done():
            scheduler_task.cancel()
            await asyncio.wait([scheduler_task], timeout=5.0)  # Laisse 5s pour s'arrêter

        # Arrête le bot proprement
        if bot_app.updater and bot_app.updater.running:
            await bot_app.updater.stop()
        if bot_app.running:
            await bot_app.stop()

        logger.info("Services arrêtés. Au revoir.")


if __name__ == "__main__":
    # Point d'entrée pour la commande: python main.py
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "cannot run" in str(e) and sys.platform == "win32":
            # Un fix commun pour asyncio sur Windows
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            asyncio.run(main())
        else:
            raise e