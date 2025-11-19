import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')

# --- DÉFINITION DU CLAVIER PRINCIPAL ---
# Cette fonction sera importée par TOUTES vos autres commandes
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
            InlineKeyboardButton("🔄 刷新 (Rafraîchir)", callback_data="nav_main") # Bouton pour recharger
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Définitions des sous-menus ---

def get_monitors_menu_keyboard():
    """Retourne le clavier du menu Moniteurs (juste un bouton retour)."""
    keyboard = [
        [InlineKeyboardButton("« 返回主菜单 (Retour Menu Principal)", callback_data="nav_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_proxies_menu_keyboard():
    """Retourne le clavier du menu Proxies (juste un bouton retour)."""
    keyboard = [
        [InlineKeyboardButton("« 返回主菜单 (Retour Menu Principal)", callback_data="nav_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_menu_keyboard():
    """Retourne le clavier du menu Admin (juste un bouton retour)."""
    keyboard = [
        [InlineKeyboardButton("« 返回主菜单 (Retour Menu Principal)", callback_data="nav_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Textes des menus (en Chinois Simplifié) ---
# Vous pouvez les copier depuis ma réponse précédente
MAIN_MENU_TEXT = "你好！欢迎使用X监控机器人。\n\n请从下方选择一个类别："
MONITORS_MENU_TEXT = "📊 **监控管理**\n\n使用以下命令来管理监控:\n`/list_watches` \- 查看所有监控\n`/add_watch` \- 添加监控\n..."
PROXIES_MENU_TEXT = "🛡️ **代理管理**\n\n`/proxy_list` \- 列出所有代理\n`/proxy_add` \- 添加代理\n..."
ADMIN_MENU_TEXT = "🔑 **管理员设置**\n\n`/whitelist_add` \- 添加管理员\n`/whitelist_remove` \- 删除管理员\n..."

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
    Gère l'arbre de navigation.
    """
    query = update.callback_query
    await query.answer()  # Confirme la réception du clic

    data = query.data
    text = ""
    keyboard = None

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
    else:
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
        # Si l'édition échoue (ex: message trop ancien), on en envoie un nouveau
        await query.message.reply_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        )