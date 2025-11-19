import logging
import asyncio
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from core.auth import whitelist_required
from .menu import get_main_menu_keyboard

logger = logging.getLogger('TelegramBot')

SCHEDULER_KEY = 'scheduler_status'
WORKERS_KEY = 'worker_tasks'
TELEGRAM_MAX_MESSAGE_LENGTH = 4096


async def send_long_message(update: Update, text: str, parse_mode: str = None):
    """
    Découpe et envoie un long message en plusieurs parties.
    Le clavier principal n'est attaché qu'au dernier message.
    """
    parts = []
    current = ""

    for line in text.split("\n"):
        if len(current) + len(line) + 1 > TELEGRAM_MAX_MESSAGE_LENGTH:
            parts.append(current.strip())
            current = line + "\n"
        else:
            current += line + "\n"

    if current:
        parts.append(current.strip())

    for i, part in enumerate(parts):
        prefix = ""
        reply_markup = None

        if i > 0:
            prefix = rf"\[继续 \- 第 {i + 1}/{len(parts)} 部分\]\n"

        if i == len(parts) - 1:
            reply_markup = get_main_menu_keyboard()

        await update.message.reply_text(
            prefix + part,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )

        if len(parts) > 2:
            await asyncio.sleep(0.5)


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Affiche l'état du Scheduler et des Workers.
    """
    out = []
    out.append("⚙️ **调度器 \\(Scheduler\\) 状态** ⚙️\n")

    # ----- 1. Scheduler -----
    scheduler = context.bot_data.get(SCHEDULER_KEY, {})

    if not scheduler:
        out.append("🛑 调度器状态未初始化。管理器可能尚未启动。")
        is_running = False
        queue_size = "N/A"
    else:
        is_running = scheduler.get("running", False)
        last_run = scheduler.get("last_run", "从不")
        interval_sec = scheduler.get("interval_sec", "N/A")
        queue_size = scheduler.get("queue_size", "N/A")

        emoji = "✅" if is_running else "❌"

        out.append(f"通用状态: **{emoji} {str(is_running)}**")
        out.append(f"上次运行周期: `{escape_markdown(last_run, 2)}`")
        out.append(f"待处理任务: **{queue_size}**")
        out.append(f"间隔时间: **{interval_sec} 秒**")

    # ----- 2. Workers -----
    out.append("\n🧑‍💻 **Worker \\(任务消费者\\) 状态** 🧑‍💻")

    worker_tasks: list = context.bot_data.get(WORKERS_KEY, [])

    if not worker_tasks:
        out.append("未启动任何 Worker。")
    else:
        total = len(worker_tasks)
        active = sum(1 for task in worker_tasks if not task.done() and not task.cancelled())
        inactive = total - active

        out.append(f"Worker 总数: **{total}**")
        out.append(f"活跃 Worker: **{active}**")
        out.append(f"不活跃 Worker: **{inactive}**")

        if inactive > 0:
            out.append(
                f"⚠️ **{inactive}** 个 Worker 已完成或被取消。如果不是预期的，可能需要重启。"
            )

    final_message = "\n".join(out)

    await send_long_message(
        update,
        final_message,
        parse_mode=ParseMode.MARKDOWN_V2
    )
