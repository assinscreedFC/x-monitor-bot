import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from core.auth import whitelist_required
import time  # Nécessaire pour forcer le rafraîchissement du menu
from telegram import Update  # Nécessaire pour la simulation d'objet Update

logger = logging.getLogger('TelegramBot')


# --- DÉFINITION DU CLAVIER PRINCIPAL (BASE) ---

def get_main_menu_keyboard():
    """Retourne le clavier InlineKeyboardMarkup du menu principal."""
    keyboard = [
        [
            InlineKeyboardButton("📊 监控管理 (Gestion Moniteurs)", callback_data="nav_monitors"),
        ],
        [
            InlineKeyboardButton("🛡️ 代理管理 (Gestion Proxy)", callback_data="nav_proxies"),
            InlineKeyboardButton("🔑 管理员 (Admin)", callback_data="nav_admin"),
        ],
        [
            InlineKeyboardButton("🔄 刷新 (Rafraîchir)", callback_data="nav_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# --- Définitions des sous-menus (AVEC BOUTONS D'ACTION) ---

def get_monitors_menu_keyboard():
    """Clavier pour le sous-menu Moniteurs."""
    keyboard = [
        [
            InlineKeyboardButton("🗒️ 查看所有监控 (/list_watches)", callback_data="act_list_watches"),
            InlineKeyboardButton("➕ 添加监控 (/add_watch)", callback_data="act_add_watch"),
        ],
        [
            InlineKeyboardButton("❌ 删除监控 (/remove_watch)", callback_data="act_remove_watch"),
        ],
        [
            InlineKeyboardButton("▶️ 启动监控 (/start_monitor)", callback_data="act_start_monitor"),
            InlineKeyboardButton("⏸️ Arrêter surveillance (/stop_monitor)", callback_data="act_stop_monitor"),
        ],
        [InlineKeyboardButton("« 返回主菜单 (Retour Menu Principal)", callback_data="nav_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_proxies_menu_keyboard():
    """Clavier pour le sous-menu Proxies."""
    keyboard = [
        [
            InlineKeyboardButton("📡 查看代理列表 (/proxy_list)", callback_data="act_proxy_list"),
            InlineKeyboardButton("➕ 添加代理 (/proxy_add)", callback_data="act_proxy_add"),
        ],
        [
            InlineKeyboardButton("❌ 删除代理 (/proxy_remove)", callback_data="act_proxy_remove"),
            InlineKeyboardButton("🔄 启用代理 (/proxy_enable)", callback_data="act_proxy_enable"),
        ],
        [InlineKeyboardButton("« 返回主菜单 (Retour Menu Principal)", callback_data="nav_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_menu_keyboard():
    """Clavier pour le sous-menu Admin."""
    keyboard = [
        [
            InlineKeyboardButton("➕ 添加管理员 (/whitelist_add)", callback_data="act_whitelist_add"),
            InlineKeyboardButton("❌ 删除管理员 (/whitelist_remove)", callback_data="act_whitelist_remove"),
        ],
        [
            InlineKeyboardButton("💻 Worker 详细状态 (/worker_status)", callback_data="act_worker_status"),
            InlineKeyboardButton("⚙️ 系统状态 (/status)", callback_data="act_status"),
        ],
        [InlineKeyboardButton("« 返回主菜单 (Retour Menu Principal)", callback_data="nav_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


# --- Textes des menus ---
MAIN_MENU_TEXT = "你好！欢迎使用X监控机器人。\n\n请从下方选择一个类别："

# Correction pour éviter les SyntaxWarnings
MONITORS_MENU_TEXT = rf"📊 **监控管理**\n\n请选择操作，或使用 /add\_watch, /remove\_watch 等命令直接输入参数。"
PROXIES_MENU_TEXT = rf"🛡️ **代理管理**\n\n请选择操作，或使用 /proxy\_add, /proxy\_remove 等命令直接输入参数。"
ADMIN_MENU_TEXT = rf"🔑 **管理员设置**\n\n请选择操作，或使用 /whitelist\_add, /status 等命令直接输入参数。"


# --- FONCTIONS UTILITAIRES D'USAGE ---

def get_usage_text(action: str) -> str:
    """Retourne le texte d'aide basé sur l'action."""

    if action == "act_list_watches":
        return rf"🗒️ 查看所有监控：\n\n请直接发送命令：`/list_watches`"

    elif action == "act_status":
        return rf"⚙️ 系统状态：\n\n请直接发送命令：`/status`"

    elif action == "act_worker_status":
        return rf"💻 Worker 状态：\n\n请直接发送命令：`/worker_status`"

    elif action == "act_proxy_list":
        return rf"📡 查看代理列表：\n\n请直接发送命令：`/proxy_list`"

    # --- COMMANDES AVEC ARGUMENTS ---
    elif action == "act_add_watch":
        return (
            rf"➕ **添加监控**\n\n请发送以下命令格式：\n"
            rf"`/add_watch <X账户> <ChatID>`\n"
            rf"**示例:** `/add_watch elonmusk -100123456789`"
        )
    elif action == "act_remove_watch":
        return (
            rf"❌ **删除监控**\n\n请发送以下命令格式：\n"
            rf"`/remove_watch <监控 ID>`\n"
            rf"**示例:** `/remove_watch 123`"
        )
    elif action == "act_start_monitor":
        return rf"▶️ **启动监控**\n\n请发送以下命令格式：\n\n`/start_monitor <监控 ID>`"

    elif action == "act_stop_monitor":
        return rf"⏸️ **停止监控**\n\n请发送以下命令格式：\n\n`/stop_monitor <监控 ID>`"

    elif action == "act_proxy_add":
        return (
            rf"➕ **添加代理**\n\n请发送以下命令格式：\n"
            rf"`/proxy_add <ip:port>`\n"
            rf"**示例:** `/proxy_add 1.2.3.4:8080`"
        )
    elif action == "act_proxy_remove":
        return rf"❌ **删除代理**\n\n请发送以下命令格式：\n\n`/proxy_remove <代理 ID>`"

    elif action == "act_proxy_enable":
        return rf"🔄 **启用代理**\n\n请发送以下命令格式：\n\n`/proxy_enable <代理 ID>`"

    elif action == "act_whitelist_add":
        return rf"➕ **添加管理员**\n\n请发送以下命令格式：\n\n`/whitelist_add <用户 ID>`"

    elif action == "act_whitelist_remove":
        return rf"❌ **删除管理员**\n\n请发送以下命令格式：\n\n`/whitelist_remove <用户 ID>`"

    return "错误：未知的操作。"


@whitelist_required
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le menu principal (pour /start ou /menu)."""
    await update.message.reply_text(
        MAIN_MENU_TEXT,
        reply_markup=get_main_menu_keyboard()
    )


@whitelist_required
async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Routeur central pour TOUS les clics de boutons (CallbackQuery).
    Gère l'arbre de navigation et l'affichage des commandes.
    """
    query = update.callback_query
    await query.answer()

    data = query.data
    text = ""
    keyboard = None

    # --- NAVIGATION ENTRE MENUS (nav_...) ---

    if data == "nav_main":
        # Force l'édition pour éviter "Message is not modified"
        timestamp = int(time.time())
        text = MAIN_MENU_TEXT + rf"\n`[状态更新: {timestamp}]`"  # Ajout d'un timestamp invisible
        keyboard = get_main_menu_keyboard()
    elif data == "nav_monitors":
        text = MONITORS_MENU_TEXT
        keyboard = get_monitors_menu_keyboard()
    elif data == "nav_proxies":
        text = PROXIES_MENU_TEXT
        keyboard = get_proxies_menu_keyboard()
    elif data == "nav_admin":
        text = ADMIN_MENU_TEXT
        keyboard = get_admin_menu_keyboard()

    # --- EXECUTION D'ACTIONS (act_...) ---

    elif data.startswith("act_"):

        cmd_name = data.replace('act_', '')
        handler_func = context.bot_data.get('command_map', {}).get(cmd_name)

        if handler_func:
            # --- APPEL DIRECT DE LA FONCTION (Pour les commandes sans argument) ---

            # 1. Supprimer les boutons du message original
            await query.edit_message_reply_markup(reply_markup=None)

            # 2. Créer un objet Update simulé pour la fonction execute.
            fake_update = Update(
                update_id=update.update_id,
                message=query.message,  # Utilise le message qui contient le bouton
            )

            # 3. Exécuter la fonction de commande directement (C'est le FIX !)
            await handler_func(fake_update, context)

            return  # Le handler_func s'est exécuté et a affiché le résultat + le menu.

        else:
            # Commandes AVEC arguments : Affiche le format d'usage et retourne au sous-menu

            text = get_usage_text(data)

            # Déterminer le clavier de retour
            if cmd_name in ["add_watch", "remove_watch", "start_monitor", "stop_monitor"]:
                keyboard = get_monitors_menu_keyboard()
            elif cmd_name in ["proxy_add", "proxy_remove", "proxy_enable"]:
                keyboard = get_proxies_menu_keyboard()
            elif cmd_name in ["whitelist_add", "whitelist_remove"]:
                keyboard = get_admin_menu_keyboard()

            # Pas de 'return' ici, on passe à l'édition du message ci-dessous

    else:
        # Message par défaut si callback_data inconnu
        text = "错误：未知的导航。 (Erreur: Navigation inconnue)"
        keyboard = get_main_menu_keyboard()

    # Modifie le message existant pour les navigations/usages
    try:
        await query.edit_message_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.warning(f"Erreur lors de l'édition du message (menu) : {e}")
        # Si l'édition échoue, on envoie un nouveau message
        await query.message.reply_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        )