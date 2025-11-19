import logging
import html
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from core.auth import whitelist_required
from .menu import get_main_menu_keyboard  # Pour attacher le menu

logger = logging.getLogger('TelegramBot')

# --- Base de Connaissances des Commandes (TRADUCTION) ---
COMMAND_INFO = {
    "start": {
        "usage": "/start",
        "short_desc": "启动机器人并显示欢迎信息。",
        "long_desc": "启动机器人并显示欢迎信息，指导您使用 /help 查看完整功能列表。"
    },
    "help": {
        "usage": "/help [命令名称]",
        "short_desc": "显示此命令列表或特定命令的详细信息。",
        "long_desc": "使用 /help 查看通用列表。\n使用 `/help <命令名称>` (例如: `/help add_watch`) 查看其用法、参数和效果的详细信息。"
    },
    "status": {
        "usage": "/status",
        "short_desc": "显示系统当前状态 (调度器、Worker、任务队列)。",
        "long_desc": "提供异步监控引擎的状态概览、任务队列大小和 Worker 的运行状态。"
    },
    "add_watch": {
        "usage": "/add_watch <@X账户> [inclure_liens: true/false]",
        "short_desc": "添加要监控的 X/Twitter 账户。",
        "long_desc": "添加一个新的监控。机器人会将该账户的新帖子发送到当前聊天。\n第二个可选参数用于选择发送的消息是否应包含链接。默认值: true。"
    },
    "remove_watch": {
        "usage": "/remove_watch <监控_ID>",
        "short_desc": "通过 ID 删除监控。",
        "long_desc": "需要删除的监控 ID。使用 `/list_watches` 获取 ID。此操作永久移除监控。"
    },
    "list_watches": {
        "usage": "/list_watches",
        "short_desc": "列出所有启用和禁用的监控。",
        "long_desc": "显示监控器列表，包括其 ID、监控的 X 账户、状态 (启用/禁用) 和上次查看帖子的日期。"
    },
    "start_monitor": {
        "usage": "/start_monitor",
        "short_desc": "启动调度器循环 (生产者/Worker)。",
        "long_desc": "初始化监控引擎。适用于机器人刚启动或系统通过 `/stop_monitor` 停止的情况。"
    },
    "stop_monitor": {
        "usage": "/stop_monitor",
        "short_desc": "停止调度器循环 (暂停 Worker)。",
        "long_desc": "干净地停止监控任务的生成。Worker 完成当前任务后暂停。"
    },
    "proxy_add": {
        "usage": "/proxy_add <http://ip:port>",
        "short_desc": "将代理添加到轮换列表。",
        "long_desc": "添加一个新的代理 URL 进行抓取。URL 必须是 `http://ip:port`。用户名和密码从 .env 文件读取。"
    },
    "proxy_list": {
        "usage": "/proxy_list",
        "short_desc": "显示所有已注册代理的状态。",
        "long_desc": "列出所有代理、其 ID、状态 (活动/禁用) 和错误计数器。用于查看哪些代理已停止服务。"
    },
    "proxy_remove": {
        "usage": "/proxy_remove <代理_ID>",
        "short_desc": "通过 ID 删除代理。",
        "long_desc": "永久从轮换列表中移除一个代理。使用 `/proxy_list` 获取 ID。"
    },
    "proxy_enable": {
        "usage": "/proxy_enable <代理_ID>",
        "short_desc": "重新激活禁用的代理并重置其错误计数器。",
        "long_desc": "当代理达到错误阈值 (通常为 5) 后被禁用时，此命令允许手动将其恢复服务。"
    },
    "whitelist_add": {
        "usage": "/whitelist_add <用户_ID>",
        "short_desc": "将用户添加到授权管理员列表。",
        "long_desc": "授权 Telegram 用户 (通过其数字 ID 识别) 使用受保护的命令。"
    },
    "whitelist_remove": {
        "usage": "/whitelist_remove <用户_ID>",
        "short_desc": "从管理员白名单中删除用户。",
        "long_desc": "移除用户对管理命令的访问权限。注意：不能移除最后一个管理员。"
    },
}

# -------------------------------------------

async def _send_general_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche la liste courte des commandes en HTML."""
    message = "<b>🤖 可用命令列表 🤖</b>\n\n"
    message += "<b>--- 🛡️ 管理员命令 (全部受保护) 🛡️ ---</b>\n"

    admin_commands = sorted(COMMAND_INFO.keys())

    for cmd_name in admin_commands:
        info = COMMAND_INFO[cmd_name]
        safe_desc = html.escape(info['short_desc'])
        message += f"• <code>/{cmd_name}</code>: {safe_desc}\n"

    message += "\n要获取使用详情 (所需参数)，请使用:\n"
    message += "<code>/help &lt;命令名称&gt;</code> (例如: <code>/help add_watch</code>)"

    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard()
    )


async def _send_detailed_help(update: Update, context: ContextTypes.DEFAULT_TYPE, cmd_name: str):
    """Affiche l'aide détaillée pour une commande spécifique en HTML."""
    cmd_name = cmd_name.lstrip('/').lower()
    info = COMMAND_INFO.get(cmd_name)

    if not info:
        error_message = f"⚠️ 命令 /{html.escape(cmd_name)} 未找到。请使用 /help 查看完整列表。"
        await update.message.reply_text(
            error_message,
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
        )
        return

    message = f"<b>📚 详细帮助：/{html.escape(cmd_name)}</b>\n"
    message += f"<b>用法 (Usage):</b> <code>{html.escape(info['usage'])}</code>\n"
    message += f"<b>描述 (Description):</b> {html.escape(info['long_desc'])}"

    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard()
    )


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Point d'entrée principal pour la commande /help, désormais protégée.
    """
    if not update.message:
        return

    if not context.args:
        # /help sans argument -> aide générale
        await _send_general_help(update, context)
    else:
        # /help <nom_commande> -> aide détaillée
        cmd_name = context.args[0]
        await _send_detailed_help(update, context, cmd_name)
