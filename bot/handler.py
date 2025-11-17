from telegram.ext import Application, CommandHandler, MessageHandler, filters
from core.auth import whitelist_required
from .commands import start
from .commands import help  # <-- NOUVEL IMPORT
from .commands import add_watch
from .commands import whitelist_add
from .commands import whitelist_remove
from .commands import list_watches
from .commands import remove_watch
from .commands import monitor_control
from .commands import status
from .commands import proxy_add
from .commands import proxy_list
from .commands import proxy_remove


def register_handlers(app: Application):
    """
    Attache tous les gestionnaires de commandes à l'application bot.
    """

    # --- COMMANDES DÉPROTÉGÉES ---
    app.add_handler(CommandHandler("start", start.execute))
    app.add_handler(CommandHandler("help", help.execute))  # <-- NOUVEL HANDLER

    # --- COMMANDES PROTÉGÉES (AVEC DÉCORATEUR) ---

    # Gestion des moniteurs
    app.add_handler(CommandHandler("add_watch", whitelist_required(add_watch.execute)))
    app.add_handler(CommandHandler("list_watches", whitelist_required(list_watches.execute)))
    app.add_handler(CommandHandler("remove_watch", whitelist_required(remove_watch.execute)))

    # Contrôle des moniteurs
    app.add_handler(CommandHandler("start_monitor", monitor_control.start_monitor))
    app.add_handler(CommandHandler("stop_monitor", monitor_control.stop_monitor))

    # Gestion des admins
    app.add_handler(CommandHandler("whitelist_add", whitelist_required(whitelist_add.execute)))
    app.add_handler(CommandHandler("whitelist_remove", whitelist_required(whitelist_remove.execute)))

    # Gestion des proxies
    app.add_handler(CommandHandler("proxy_add", whitelist_required(proxy_add.execute)))
    app.add_handler(CommandHandler("proxy_list", whitelist_required(proxy_list.execute)))
    app.add_handler(CommandHandler("proxy_remove", whitelist_required(proxy_remove.execute)))

    # Statut du système
    app.add_handler(CommandHandler("status", whitelist_required(status.execute)))