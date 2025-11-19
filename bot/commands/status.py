import logging
import time
import os
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
import asyncio
from telegram.helpers import escape_markdown
from .menu import get_main_menu_keyboard  # <-- Import du clavier principal

from core.json_manager import storage_manager, MONITORS_FILE, WHITELIST_FILE
from core.auth import whitelist_required
from config import settings

logger = logging.getLogger('TelegramBot')

# Constante Telegram pour la limite de message
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
            header = rf"\[继续 \- 第 {i + 1}/{len(parts)} 部分\]\n"
        await update.message.reply_text(header + part, parse_mode=parse_mode, reply_markup=reply_markup)

        if len(parts) > 2:
            await asyncio.sleep(0.5)


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Affiche un aperçu du statut du bot (nombre de moniteurs, utilisateurs, etc.).
    """
    response_parts = ["✨ **系统状态总览** ✨\n"]  # <-- TRADUCTION

    try:
        # 1. Moniteurs
        monitors = await storage_manager.read_data(MONITORS_FILE)
        active_monitors = sum(1 for m in monitors if m.get('enabled', False))
        inactive_monitors = len(monitors) - active_monitors

        response_parts.append(f"📡 **监控总数:** {len(monitors)}")  # <-- TRADUCTION
        response_parts.append(f"   • 已启用 (活跃): {active_monitors} ✅")  # <-- TRADUCTION
        response_parts.append(f"   • 已禁用 (不活跃): {inactive_monitors} ❌")  # <-- TRADUCTION

        # 2. Whitelist
        whitelist = await storage_manager.read_data(WHITELIST_FILE)
        response_parts.append(f"\n👤 **白名单管理员:** {len(whitelist)}")  # <-- TRADUCTION

        # 3. Dernier check (basé sur la modification du fichier)
        response_parts.append("\nℹ️ **数据库信息:**")  # <-- TRADUCTION

        monitors_path = os.path.join(settings.STORAGE_DIR, MONITORS_FILE)

        if os.path.exists(monitors_path):
            last_monitor_mod = time.ctime(os.path.getmtime(monitors_path))

            # Échapper la date/heure car elle peut contenir des espaces ou des :
            safe_date = escape_markdown(last_monitor_mod, version=2)

            response_parts.append(f"   • 监控最后修改: `{safe_date}`")  # <-- TRADUCTION
        else:
            response_parts.append("   • 未找到监控文件。")  # <-- TRADUCTION

    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {e}")
        # Échapper l'erreur pour le message Telegram
        safe_error = escape_markdown(str(e), version=2)
        response_parts.append(rf"🛑 **系统错误:** 读取文件时出现问题 \({safe_error}\)")
    final_message = "\n".join(response_parts)

    # Utilisation de la nouvelle fonction pour gérer le découpage et le menu
    await send_long_message(
        update,
        final_message,
        parse_mode=ParseMode.MARKDOWN_V2
    )