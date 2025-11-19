import logging
import html
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from core.json_manager import storage_manager, PROXIES_FILE
from core.auth import whitelist_required
from .menu import get_main_menu_keyboard

logger = logging.getLogger('TelegramBot')

NEW_ERROR_COUNT = 0


async def _set_proxy_status(proxy_id: int, status: bool) -> (bool, str):
    """
    Active/Désactive un proxy et réinitialise son compteur d'erreurs.
    Retourne (succès, message).
    """
    proxies = await storage_manager.read_data(PROXIES_FILE)

    safe_proxy_id = html.escape(str(proxy_id))

    proxy_index = next((i for i, p in enumerate(proxies) if p['id'] == proxy_id), None)

    if proxy_index is None:
        return False, f"Proxy ID <code>{safe_proxy_id}</code> 未找到 (Non trouvé)."

    proxies[proxy_index]['active'] = status
    proxies[proxy_index]['error_count'] = NEW_ERROR_COUNT

    await storage_manager.write_data(PROXIES_FILE, proxies)

    proxy_url_display = proxies[proxy_index]['proxy_url'][:30] + "..."
    safe_proxy_url = html.escape(proxy_url_display)

    return True, (
        f"Proxy <code>{safe_proxy_url}</code> 成功重新启用 (Réactivé avec succès). "
        f"错误计数器已重置 (Compteur d'erreurs réinitialisé)."
    )


@whitelist_required
async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Réactive un proxy désactivé et réinitialise son compteur d'erreurs.
    Usage: /proxy_enable <ID_du_proxy>
    """
    # Vérification des arguments
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "用法: <b>/proxy_enable &lt;代理_ID&gt;</b><br>"
            "使用 <b>/proxy_list</b> 查看 ID。",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Conversion de l'ID
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "⛔ ID 必须是一个整数。",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Action principale
    success, message = await _set_proxy_status(target_id, status=True)

    safe_message = message  # déjà échappé dans _set_proxy_status

    if success:
        logger.info(f"Proxy ID {target_id} réactivé par {update.effective_user.username}")
        await update.message.reply_text(
            f"✅ 操作成功 (Opération réussie)!<br>{safe_message}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            f"⚠️ 重新启用失败 (Échec de la réactivation):<br>{safe_message}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
        )
