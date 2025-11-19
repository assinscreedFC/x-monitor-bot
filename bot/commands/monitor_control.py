import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from core.json_manager import storage_manager, MONITORS_FILE
from core.auth import whitelist_required
from telegram.helpers import escape_markdown  # Pour l'échappement des logs
from .menu import get_main_menu_keyboard  # Pour attacher le menu

logger = logging.getLogger('TelegramBot')


async def set_monitor_status(update: Update, context: ContextTypes.DEFAULT_TYPE, should_enable: bool):
    """
    Fonction utilitaire pour démarrer ou arrêter un moniteur.
    """
    # TRADUCTION DE L'ACTION
    action_zh = "启动" if should_enable else "停止"
    action_en = "démarrer" if should_enable else "arrêter"

    # 1. Vérifier les arguments
    if not context.args or len(context.args) != 1:
        # TRADUCTION DU MESSAGE D'ERREUR D'USAGE
        await update.message.reply_text(
            rf"用法: /\{action_en}\_monitor <监控\_ID> (查看 /list\_watches)",
            reply_markup=get_main_menu_keyboard(),  # <-- ATTACHER LE MENU
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        target_id = int(context.args[0])
        safe_id = escape_markdown(str(target_id), version=2)  # Échapper l'ID pour le message final
    except ValueError:
        # TRADUCTION DU MESSAGE D'ERREUR DE VALEUR
        await update.message.reply_text(
            "⛔ 监控 ID 必须是一个整数。",
            reply_markup=get_main_menu_keyboard(),  # <-- ATTACHER LE MENU
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    # 2. Lire et modifier
    monitors = await storage_manager.read_data(MONITORS_FILE)
    found = False

    for m in monitors:
        if m.get('id') == target_id:
            if m.get('enabled') == should_enable:
                # TRADUCTION DU MESSAGE DE STATUT DÉJÀ EXISTANT
                status_text_zh = "已启用" if should_enable else "已停止"

                await update.message.reply_text(
                    rf"⚠️ 监控 ID `{safe_id}` 状态已经是 {status_text_zh}\.",
                    reply_markup=get_main_menu_keyboard(),  # <-- ATTACHER LE MENU
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                return

            # Modifier l'état
            m['enabled'] = should_enable
            found = True
            break

    if not found:
        # TRADUCTION DU MESSAGE D'ERREUR NON TROUVÉ
        await update.message.reply_text(
            rf"⚠️ 监控 ID `{safe_id}` 未找到\.",
            reply_markup=get_main_menu_keyboard(),  # <-- ATTACHER LE MENU
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    # 3. Sauvegarder et informer
    await storage_manager.write_data(MONITORS_FILE, monitors)

    # TRADUCTION DU MESSAGE DE SUCCÈS
    status_text_zh = "已启用 (将在下一个周期开始)" if should_enable else "已停止"

    logger.info(f"Moniteur ID {target_id} {action_en} par {update.effective_user.username}")

    await update.message.reply_text(
        rf"✅ 监控 ID **`{safe_id}`** {status_text_zh}\.",
        reply_markup=get_main_menu_keyboard(),  # <-- ATTACHER LE MENU
        parse_mode=ParseMode.MARKDOWN_V2
    )


@whitelist_required
async def start_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Démarre une surveillance."""
    await set_monitor_status(update, context, True)


@whitelist_required
async def stop_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Arrête une surveillance."""
    await set_monitor_status(update, context, False)