import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from core.json_manager import storage_manager, PROXIES_FILE
from core.auth import whitelist_required
from telegram.helpers import escape_markdown
from .menu import get_main_menu_keyboard  # <-- Import du clavier principal

logger = logging.getLogger('TelegramBot')

# Constante pour réinitialiser le compteur d'erreurs
NEW_ERROR_COUNT = 0


async def _set_proxy_status(proxy_id: int, status: bool) -> (bool, str):
    """
    Met à jour l'état (actif/inactif) d'un proxy et réinitialise les erreurs.
    Retourne (succès, message_détail).
    """
    proxies = await storage_manager.read_data(PROXIES_FILE)

    # Convertir l'ID du proxy en string pour l'affichage, car il est une variable essentielle ici
    safe_proxy_id = escape_markdown(str(proxy_id), version=2)

    proxy_index = next((i for i, p in enumerate(proxies) if p['id'] == proxy_id), None)

    if proxy_index is None:
        # TRADUCTION DE L'ERREUR NON TROUVÉ
        return False, f"Proxy ID `{safe_proxy_id}` 未找到 (Non trouvé)\."

    # Mise à jour de l'état
    proxies[proxy_index]['active'] = status
    proxies[proxy_index]['error_count'] = NEW_ERROR_COUNT

    await storage_manager.write_data(PROXIES_FILE, proxies)

    # TRADUIRE ET ÉCHAPPER LE MESSAGE DE SUCCÈS
    proxy_url_display = proxies[proxy_index]['proxy_url'][:30] + "..."
    safe_proxy_url = escape_markdown(proxy_url_display, version=2)

    return True, rf"Proxy `{safe_proxy_url}` 成功重新启用 (Réactivé avec succès)\. 错误计数器已重置 (Compteur d'erreurs réinitialisé)\."


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Réactive un proxy désactivé par le système et réinitialise son compteur d'erreurs.
    Usage: /proxy_enable <ID_du_proxy>
    """
    # 1. Vérifier l'usage (TRADUCTION)
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "用法: /proxy\_enable <代理\_ID> (使用 /proxy\_list 查看 ID)",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
        )
        return

    # 2. Valider l'ID
    try:
        target_id = int(context.args[0])
    except ValueError:
        # TRADUCTION DE L'ERREUR DE VALEUR
        await update.message.reply_text(
            "⛔ ID 必须是一个整数。",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
        )
        return

    # 3. Exécuter la mise à jour
    success, message = await _set_proxy_status(target_id, status=True)

    # 4. Réponse
    if success:
        logger.info(f"Proxy ID {target_id} réactivé par {update.effective_user.username}")
        # Message de succès (le message est déjà échappé par _set_proxy_status)
        await update.message.reply_text(
            rf"✅ 操作成功 (Opération réussie)!\n{message}",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
        )
    else:
        # Message d'échec (le message est déjà échappé ou contient l'erreur)
        await update.message.reply_text(
            rf"⚠️ 重新启用失败 (Échec de la réactivation): {message}",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=get_main_menu_keyboard()  # <-- ATTACHER LE MENU
        )