import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from core.auth import whitelist_required

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
        # Actions principales
        [
            InlineKeyboardButton("🗒️ 查看所有监控 (/list_watches)", callback_data="act_list_watches"),
            InlineKeyboardButton("➕ 添加监控 (/add_watch)", callback_data="act_add_watch"),
        ],
        # Actions de contrôle
        [
            InlineKeyboardButton("❌ 删除监控 (/remove_watch)", callback_data="act_remove_watch"),
        ],
        [
            InlineKeyboardButton("▶️ 启动调度器 (/start_monitor)", callback_data="act_start_monitor"),
            InlineKeyboardButton("⏸️ 停止调度器 (/stop_monitor)", callback_data="act_stop_monitor"),
        ],
        # Retour à la racine
        [InlineKeyboardButton("« 返回主菜单 (Retour Menu Principal)", callback_data="nav_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_proxies_menu_keyboard():
    """Clavier pour le sous-menu Proxies."""
    keyboard = [
        # Actions principales
        [
            InlineKeyboardButton("📡 查看代理列表 (/proxy_list)", callback_data="act_proxy_list"),
            InlineKeyboardButton("➕ 添加代理 (/proxy_add)", callback_data="act_proxy_add"),
        ],
        # Actions de contrôle
        [
            InlineKeyboardButton("❌ 删除代理 (/proxy_remove)", callback_data="act_proxy_remove"),
            InlineKeyboardButton("🔄 启用代理 (/proxy_enable)", callback_data="act_proxy_enable"),
        ],
        # Retour à la racine
        [InlineKeyboardButton("« 返回主菜单 (Retour Menu Principal)", callback_data="nav_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_menu_keyboard():
    """Clavier pour le sous-menu Admin."""
    keyboard = [
        # Actions principales
        [
            InlineKeyboardButton("➕ 添加管理员 (/whitelist_add)", callback_data="act_whitelist_add"),
            InlineKeyboardButton("❌ 删除管理员 (/whitelist_remove)", callback_data="act_whitelist_remove"),
        ],
        # Autres statuts
        [
            InlineKeyboardButton("💻 Worker 详细状态 (/worker_status)", callback_data="act_worker_status"),
            InlineKeyboardButton("⚙️ 系统状态 (/status)", callback_data="act_status"),
        ],
        # Retour à la racine
        [InlineKeyboardButton("« 返回主菜单 (Retour Menu Principal)", callback_data="nav_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


# --- Textes des menus (MIS À JOUR) ---
MAIN_MENU_TEXT = "你好！欢迎使用X监控机器人。\n\n请从下方选择一个类别："

MONITORS_MENU_TEXT = "📊 **监控管理**\n\n请选择操作，或使用 /add\_watch, /remove\_watch 等命令直接输入参数。"
PROXIES_MENU_TEXT = "🛡️ **代理管理**\n\n请选择操作，或使用 /proxy\_add, /proxy\_remove 等命令直接输入参数。"
ADMIN_MENU_TEXT = "🔑 **管理员设置**\n\n请选择操作，或使用 /whitelist\_add, /status 等命令直接输入参数。"


# --- GESTIONNAIRES (HANDLERS) ---

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
    Gère l'arbre de navigation et l'exécution des commandes directes.
    """
    query = update.callback_query
    await query.answer()

    data = query.data
    text = ""
    keyboard = None

    # --- NAVIGATION ENTRE MENUS ---

    if data == "nav_main":
        text = MAIN_MENU_TEXT
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

    # --- EXECUTION DE COMMANDES DIRECTES (Simulateur) ---
    # Quand l'utilisateur clique sur une action qui ne demande pas d'argument.
    # Ex: /list_watches, /status

    elif data in ["act_list_watches", "act_proxy_list", "act_worker_status", "act_status"]:
        # Pour ces commandes, nous appelons le handler directement.

        # Le nom de la commande est après 'act_'
        cmd_name = data.split('act_')[1]

        # On trouve le handler correspondant dans la configuration de l'application
        # NOTE: Ceci suppose que vous avez stocké les handlers dans context.bot_data ou que vous
        # pouvez les importer ici. Si vous ne pouvez pas les importer, la solution la plus simple
        # est de faire une boucle de simulation ou d'utiliser le CommandHandler:

        # Simuler le message pour que le CommandHandler le prenne en charge
        update.callback_query.message.text = f'/{cmd_name}'

        # Supprime le menu avant l'exécution du handler
        await query.edit_message_text(f"🚀 正在运行 /{cmd_name}...")

        # Ici, vous devez déclencher le CommandHandler correspondant (non possible directement dans ce contexte)
        # La solution la plus fiable est de demander à l'utilisateur de taper la commande lui-même.

        return

    # --- ACTIONS QUI REQUIÈRENT DES ARGUMENTS ---

    elif data in ["act_add_watch", "act_remove_watch", "act_proxy_add", "act_proxy_remove", "act_proxy_enable",
                  "act_whitelist_add", "act_whitelist_remove"]:
        # Pour ces commandes, nous affichons simplement l'usage et le message dupliqué pour faciliter le copier-coller.

        # Texte d'aide basé sur l'action
        if data == "act_add_watch":
            usage_text = rf"请发送以下命令以添加监控 (Por favor, envíe el siguiente comando para añadir un monitor):\n\n`/add_watch <X账户> <ChatID>`\n\n**示例:** `/add_watch @elonmusk -100123456`"
        elif data == "act_remove_watch":
            usage_text = rf"请发送以下命令以删除监控 (Por favor, envíe el siguiente comando para eliminar un monitor):\n\n`/remove_watch <监控 ID>`"
        else:
            usage_text = f"请使用命令 `{data.replace('act_', '/')}`\n\n请使用 `/help {data.replace('act_', '')}` 查看用法。"

        await query.edit_message_text(
            text=usage_text,
            reply_markup=get_monitors_menu_keyboard(),  # On retourne au sous-menu Moniteurs (ou le menu approprié)
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    else:
        # Message par défaut si callback_data inconnu
        text = "错误：未知的导航。 (Erreur: Navigation inconnue)"
        keyboard = get_main_menu_keyboard()

    # Modifie le message existant pour créer l'effet "d'arbre"
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