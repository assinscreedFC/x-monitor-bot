import logging
import time
import os
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
import asyncio
from telegram.helpers import escape_markdown
from .menu import get_main_menu_keyboard

from core.json_manager import storage_manager, MONITORS_FILE, WHITELIST_FILE
from core.auth import whitelist_required
from config import settings

logger = logging.getLogger('TelegramBot')

TELEGRAM_MAX_MESSAGE_LENGTH = 4096


async def send_long_message(update: Update, text: str, parse_mode: str = None):
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
        reply_markup = get_main_menu_keyboard() if i == len(parts) - 1 else None

        if i > 0:
            header = rf"\[继续 \- 第 {i + 1}/{len(parts)} 部分\]\n"

        await update.message.reply_text(header + part, parse_mode=parse_mode, reply_markup=reply_markup)

        if len(parts) > 2:
            await asyncio.sleep(0.5)


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response_parts = ["✨ **系统状态总览** ✨\n"]

    try:
        # MONITEURS
        monitors = await storage_manager.read_data(MONITORS_FILE)
        active_monitors = sum(1 for m in monitors if m.get('enabled', False))
        inactive_monitors = len(monitors) - active_monitors

        response_parts.append(f"📡 **监控总数**\\: {len(monitors)}")
        response_parts.append(f"   \\• 启用\\(活跃\\): {active_monitors} ✅")
        response_parts.append(f"   \\• 禁用\\(不活跃\\): {inactive_monitors} ❌")

        # WHITELIST
        whitelist = await storage_manager.read_data(WHITELIST_FILE)
        response_parts.append(f"\n👤 **白名单管理员**\\: {len(whitelist)}")

        # DB
        response_parts.append("\nℹ️ **数据库信息**\\:")

        monitors_path = os.path.join(settings.STORAGE_DIR, MONITORS_FILE)

        if os.path.exists(monitors_path):
            last_monitor_mod = time.ctime(os.path.getmtime(monitors_path))
            safe_date = escape_markdown(last_monitor_mod, version=2)
            response_parts.append(f"   \\• 监控文件最后修改时间\\: `{safe_date}`")
        else:
            response_parts.append("   \\• 未找到监控文件。")

    except Exception as e:
        safe_error = escape_markdown(str(e), version=2)
        response_parts.append(rf"🛑 **系统错误**\: 读取文件时出现问题 \[{safe_error}\]")

    final_message = "\n".join(response_parts)

    await send_long_message(update, final_message, parse_mode=ParseMode.MARKDOWN_V2)
