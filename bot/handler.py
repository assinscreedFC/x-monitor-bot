from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from core.auth import whitelist_required
# --- IMPORTS DES COMMANDES ---
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
from .commands import proxy_enable
from .commands import menu
from .commands import worker_status  # AJOUT DE L'IMPORT MANQUANT

# --- MAPPAGE DES FONCTIONS POUR L'APPEL DIRECT (COMMANDES SIMPLES) ---
# Ces fonctions sont appelées directement par le menu.py, sans passer par CommandHandler.
COMMAND_MAP = {
    "list_watches": list_watches.execute,
    "status": status.execute,
    "worker_status": worker_status.execute,
    "proxy_list": proxy_list.execute,
    "help": help.execute,  # <-- AJOUT : help sans argument est simple
    "start": start.execute,  # <-- AJOUT : start sans argument est simple
}


def register_handlers(app: Application):
    """
    Attache tous les gestionnaires de commandes à l'application bot.
    """

    # 1. STOCKER L'ANNUAIRE DE FONCTIONS DANS app.bot_data
    # Ceci permet à menu.py d'appeler les fonctions directement
    app.bot_data['command_map'] = COMMAND_MAP

    # --- COMMANDES DE MENU ---
    # Ces commandes lancent le menu interactif
    app.add_handler(CommandHandler("start", whitelist_required(menu.start_command)))
    app.add_handler(CommandHandler("menu", whitelist_required(menu.start_command)))

    # --- COMMANDES EXISTANTES ---
    app.add_handler(CommandHandler("help", whitelist_required(help.execute)))

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
    app.add_handler(CommandHandler("proxy_enable", whitelist_required(proxy_enable.execute)))

    # Statut du système
    app.add_handler(CommandHandler("status", whitelist_required(status.execute)))

    # --- GESTIONNAIRE DE CLICS ---
    app.add_handler(CallbackQueryHandler(whitelist_required(menu.button_router)))