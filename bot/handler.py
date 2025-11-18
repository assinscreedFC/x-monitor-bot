from telegram.ext import Application, CommandHandler, MessageHandler, filters
from core.auth import whitelist_required
from .commands import start
from .commands import help
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
from .commands import proxy_enable  # Pour la commande /proxy_enable


def register_handlers(app: Application):
    """
    Attache tous les gestionnaires de commandes à l'application bot.
    Toutes les commandes sont désormais protégées par la whitelist.
    """

    # --- COMMANDES DÉSORMAIS PROTÉGÉES ---
    # Note: La commande /whitelist_add dans son implémentation gère
    # le cas où la liste est vide.

    app.add_handler(CommandHandler("start", whitelist_required(start.execute)))
    app.add_handler(CommandHandler("help", help.execute))  # Le décorateur est dans help.py

    # --- COMMANDES PROTÉGÉES (AVEC DÉCORATEUR) ---

    # Gestion des moniteurs
    app.add_handler(CommandHandler("add_watch", whitelist_required(add_watch.execute)))
    app.add_handler(CommandHandler("list_watches", whitelist_required(list_watches.execute)))
    app.add_handler(CommandHandler("remove_watch", whitelist_required(remove_watch.execute)))

    # Contrôle des moniteurs (Décorateur intégré dans le fichier monitor_control.py)
    app.add_handler(CommandHandler("start_monitor", monitor_control.start_monitor))
    app.add_handler(CommandHandler("stop_monitor", monitor_control.stop_monitor))

    # Gestion des admins
    app.add_handler(CommandHandler("whitelist_add", whitelist_required(whitelist_add.execute)))
    app.add_handler(CommandHandler("whitelist_remove", whitelist_required(whitelist_remove.execute)))

    # Gestion des proxies
    app.add_handler(CommandHandler("proxy_add", whitelist_required(proxy_add.execute)))
    app.add_handler(CommandHandler("proxy_list", whitelist_required(proxy_list.execute)))
    app.add_handler(CommandHandler("proxy_remove", whitelist_required(proxy_remove.execute)))
    app.add_handler(CommandHandler("proxy_enable", whitelist_required(proxy_enable.execute)))

    # Statut du système
    app.add_handler(CommandHandler("status", whitelist_required(status.execute)))