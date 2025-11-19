import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
import asyncio
from core.auth import whitelist_required
from telegram.helpers import escape_markdown
from .menu import get_main_menu_keyboard  # <-- Import du clavier principal

# Déplacer ici l'utilitaire send_long_message pour la réutilisation,
# mais l'import initial suppose qu'il vient de list_watches.py.
# Pour la robustesse, je vais le redéfinir ici, incluant le clavier final.

logger = logging.getLogger('TelegramBot')

# Noms des clés que le Manager du Scheduler doit stocker dans bot_data
SCHEDULER_KEY = 'scheduler_status'
WORKERS_KEY = 'worker_tasks'
TELEGRAM_MAX_MESSAGE_LENGTH = 4096


async def send_long_message(update: Update, text: str, parse_mode: str = None):
    """
    Découpe et envoie un long message en plusieurs parties pour respecter la limite de Telegram.
    Le clavier principal est attaché à la dernière partie.
    """

    parts = []
    current_part = ""
    lines = text.split('\n')

    for line in lines:
        if len(current_part) + len(line) + 1 > TELEGRAM_MAX_MESSAGE_LENGTH:
            parts.append(current_part.strip())
            current_part = line + '\n'
        else:
            current_part += line + '\n'

    if current_part:
        parts.append(current_part.strip())

    for i, part in enumerate(parts):
        header = ""
        # On attache le menu SEULEMENT au *dernier* message.
        reply_markup = None
        if i == len(parts) - 1:
            reply_markup = get_main_menu_keyboard()  # <-- ATTACHE LE CLAVIER

        if i > 0:
            # Le header est en chinois
            header = rf"**(继续 \- 第 {i + 1}/{len(parts)} 部分)**\n"

        await update.message.reply_text(header + part, parse_mode=parse_mode, reply_markup=reply_markup)

        if len(parts) > 2:
            await asyncio.sleep(0.5)


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Affiche l'état du Scheduler (Planificateur) et des Workers (Consommateurs de tâches).
    """
    response_parts = ["⚙️ **调度器 (Scheduler) 状态** ⚙️\n"]  # <-- TRADUCTION

    # --- 1. Statut du Scheduler ---
    scheduler_status = context.bot_data.get(SCHEDULER_KEY, {})

    if not scheduler_status:
        response_parts.append("🛑 调度器状态未初始化。管理器可能尚未启动。")  # <-- TRADUCTION
        is_scheduler_running = False
        queue_size = "N/A"
    else:
        is_scheduler_running = scheduler_status.get('running', False)
        last_run_time = scheduler_status.get('last_run', '从不 (Jamais)')  # <-- TRADUCTION
        queue_size = scheduler_status.get('queue_size', 'N/A')
        interval_sec = scheduler_status.get('interval_sec', 'N/A')

        status_emoji = "✅" if is_scheduler_running else "❌"

        response_parts.append(f"通用状态: **{status_emoji} {is_scheduler_running}**")  # <-- TRADUCTION
        response_parts.append(f"上次运行周期: {escape_markdown(last_run_time, 2)}")  # <-- TRADUCTION + ÉCHAPPEMENT
        response_parts.append(f"待处理任务: **{queue_size}**")  # <-- TRADUCTION
        response_parts.append(f"间隔时间: {interval_sec} 秒")  # <-- TRADUCTION

    # --- 2. Statut des Workers ---
    response_parts.append("\n🧑‍💻 **Worker (任务消费者) 状态** 🧑‍💻")  # <-- TRADUCTION

    worker_tasks: list = context.bot_data.get(WORKERS_KEY, [])

    if not worker_tasks:
        response_parts.append("未启动任何 Worker。")  # <-- TRADUCTION
    else:
        total_workers = len(worker_tasks)
        active_workers = sum(1 for task in worker_tasks if not task.done() and not task.cancelled())
        inactive_workers = total_workers - active_workers

        response_parts.append(f"Worker 总数: **{total_workers}**")  # <-- TRADUCTION
        response_parts.append(f"活跃 Worker: **{active_workers}**")  # <-- TRADUCTION
        response_parts.append(f"不活跃 Worker: **{inactive_workers}**")

        if inactive_workers > 0:
            response_parts.append(
                f"⚠️ **{inactive_workers}** 个 Worker 已完成或被取消。如果不是预期的，可能需要重启。")  # <-- TRADUCTION

    final_message = "\n".join(response_parts)

    # Utilisation du helper pour l'envoi
    await send_long_message(
        update,
        final_message,
        parse_mode=ParseMode.MARKDOWN_V2
    )