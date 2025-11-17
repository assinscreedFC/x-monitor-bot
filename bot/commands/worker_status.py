import logging
import time
from telegram import Update
from telegram.ext import ContextTypes
import asyncio
from core.auth import whitelist_required
from bot.commands.list_watches import send_long_message  # Réutilisation de l'utilitaire

logger = logging.getLogger('TelegramBot')

# Noms des clés que le Manager du Scheduler doit stocker dans bot_data
SCHEDULER_KEY = 'scheduler_status'
WORKERS_KEY = 'worker_tasks'


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Affiche l'état du Scheduler (Planificateur) et des Workers (Consommateurs de tâches).
    """
    response_parts = ["⚙️ **Statut du Planificateur (Scheduler)** ⚙️\n"]

    # --- 1. Statut du Scheduler ---
    scheduler_status = context.bot_data.get(SCHEDULER_KEY, {})

    if not scheduler_status:
        response_parts.append("🛑 Statut du Scheduler non initialisé. Le manager n'a peut-être pas démarré.")
        is_scheduler_running = False
        queue_size = "N/A"
    else:
        is_scheduler_running = scheduler_status.get('running', False)
        last_run_time = scheduler_status.get('last_run', 'Jamais')
        queue_size = scheduler_status.get('queue_size', 'N/A')

        status_emoji = "✅" if is_scheduler_running else "❌"

        response_parts.append(f"Statut Général: **{status_emoji} {is_scheduler_running}**")
        response_parts.append(f"Dernier Cycle: {last_run_time}")
        response_parts.append(f"Tâches en Attente: **{queue_size}**")
        response_parts.append(f"Intervalle: {scheduler_status.get('interval_sec', 'N/A')} secondes")

    # --- 2. Statut des Workers ---
    response_parts.append("\n🧑‍💻 **Statut des Workers (Consommateurs)** 🧑‍💻")

    worker_tasks: list = context.bot_data.get(WORKERS_KEY, [])

    if not worker_tasks:
        response_parts.append("Aucun worker n'a été lancé.")
    else:
        total_workers = len(worker_tasks)
        active_workers = sum(1 for task in worker_tasks if not task.done() and not task.cancelled())

        response_parts.append(f"Total des Workers: **{total_workers}**")
        response_parts.append(f"Workers Actifs: **{active_workers}**")

        if active_workers < total_workers:
            response_parts.append(
                f"⚠️ **{total_workers - active_workers}** Worker(s) ont terminé ou sont annulés. Ils pourraient nécessiter un redémarrage si cela est inattendu.")

    final_message = "\n".join(response_parts)

    # Utilisation du helper pour l'envoi
    await send_long_message(
        update,
        final_message,
        parse_mode='Markdown'
    )