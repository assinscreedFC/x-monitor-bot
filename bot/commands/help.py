import logging
from telegram import Update
from telegram.ext import ContextTypes
from core.auth import whitelist_required

logger = logging.getLogger('TelegramBot')

# --- Base de Connaissances des Commandes ---
# Dictionnaire centralisant le nom, l'usage et la description des commandes.
COMMAND_INFO = {
    "start": {
        "usage": "/start",
        "short_desc": "Démarre le bot et affiche un message de bienvenue.",
        "long_desc": "Affiche le message d'accueil et vous guide vers la commande /help pour la liste complète des fonctions."
    },
    "help": {
        "usage": "/help [nom_commande]",
        "short_desc": "Affiche cette liste de commandes ou des détails sur une commande spécifique.",
        "long_desc": "Utilisez /help pour la liste générale.\nUtilisez /help <nom_commande> (ex: /help add_watch) pour des détails sur son usage, ses arguments, et ses effets."
    },
    "status": {
        "usage": "/status",
        "short_desc": "Affiche le statut actuel du système (Scheduler, Workers, File d'attente).",
        "long_desc": "Fournit un aperçu de l'état du moteur de surveillance asynchrone, de la taille de la file de tâches, et de l'état des Workers."
    },
    "add_watch": {
        "usage": "/add_watch <@compte_x> [inclure_liens: true/false]",
        "short_desc": "Ajoute un compte X/Twitter à surveiller.",
        "long_desc": "Ajoute un nouveau moniteur. Le bot enverra les nouveaux posts de ce compte dans ce chat.\nLe deuxième argument (optionnel) permet de choisir si les messages envoyés doivent inclure les liens. Par défaut : true."
    },
    "remove_watch": {
        "usage": "/remove_watch <ID_moniteur>",
        "short_desc": "Supprime une surveillance par son ID.",
        "long_desc": "Nécessite l'ID du moniteur à supprimer. Utilisez /list_watches pour trouver l'ID. Cette action retire définitivement la surveillance."
    },
    "list_watches": {
        "usage": "/list_watches",
        "short_desc": "Liste toutes les surveillances actives et désactivées.",
        "long_desc": "Affiche un tableau des moniteurs, incluant leur ID, le compte X surveillé, leur statut (activé/désactivé) et la dernière date de post vu."
    },
    "start_monitor": {
        "usage": "/start_monitor",
        "short_desc": "Démarre la boucle du Scheduler (Producteur/Workers).",
        "long_desc": "Initialise le moteur de surveillance. Utile si le bot vient d'être démarré ou si le système a été arrêté via /stop_monitor."
    },
    "stop_monitor": {
        "usage": "/stop_monitor",
        "short_desc": "Arrête la boucle du Scheduler (met les Workers en pause).",
        "long_desc": "Arrête proprement la production de tâches de surveillance. Les Workers terminent leur tâche en cours, puis se mettent en pause."
    },
    "proxy_add": {
        "usage": "/proxy_add <http://user:pass@ip:port>",
        "short_desc": "Ajoute un proxy à la liste de rotation.",
        "long_desc": "Ajoute une nouvelle URL de proxy pour le scraping. Le format doit être précis (incluant 'http://' ou 'https://' et les informations d'authentification si nécessaire)."
    },
    "proxy_list": {
        "usage": "/proxy_list",
        "short_desc": "Affiche l'état de tous les proxies enregistrés.",
        "long_desc": "Liste tous les proxies, leur ID, leur statut (actif/désactivé) et leur compteur d'erreurs. Permet de voir quels proxies sont hors service."
    },
    "proxy_remove": {
        "usage": "/proxy_remove <ID_proxy>",
        "short_desc": "Supprime un proxy par son ID.",
        "long_desc": "Retire définitivement un proxy de la liste de rotation. Utilisez /proxy_list pour obtenir l'ID."
    },
    "proxy_enable": {
        "usage": "/proxy_enable <ID_proxy>",
        "short_desc": "Réactive un proxy désactivé et réinitialise son compteur d'erreurs.",
        "long_desc": "Lorsqu'un proxy est désactivé après avoir atteint le seuil d'erreurs (souvent 5), cette commande permet de le remettre en service manuellement."
    },
    "whitelist_add": {
        "usage": "/whitelist_add <user_id>",
        "short_desc": "Ajoute un utilisateur à la liste des administrateurs autorisés.",
        "long_desc": "Autorise un utilisateur Telegram (identifié par son ID numérique) à utiliser les commandes protégées (toutes sauf /start et /help)."
    },
    "whitelist_remove": {
        "usage": "/whitelist_remove <user_id>",
        "short_desc": "Retire un utilisateur de la whitelist des administrateurs.",
        "long_desc": "Retire l'accès d'un utilisateur aux commandes d'administration. Attention : vous ne pouvez pas retirer le dernier administrateur pour éviter de bloquer le bot."
    },
}


# -------------------------------------------


async def _send_general_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche la liste courte des commandes."""
    message = "🤖 **Liste des Commandes Disponibles** 🤖\n\n"
    message += "--- 🛡️ Commandes Admin (Whitelist Required) 🛡️ ---\n"

    # Trier les commandes par catégorie (pour l'affichage)
    admin_commands = sorted([k for k, v in COMMAND_INFO.items() if k not in ["start", "help"]])

    # Construction de la liste
    for cmd_name in admin_commands:
        info = COMMAND_INFO[cmd_name]
        message += f"• `/{cmd_name}`: {info['short_desc']}\n"

    message += "\n--- 🔓 Commandes Publiques ---\n"
    message += "• `/start`: Message de bienvenue.\n"
    message += "• `/help [cmd]`: Aide détaillée.\n"

    message += "\nPour des détails sur l'usage (arguments requis), utilisez :\n"
    message += "`/help <nom_commande>` (ex: `/help add_watch`)"

    await update.message.reply_text(message, parse_mode='Markdown')


async def _send_detailed_help(update: Update, context: ContextTypes.DEFAULT_TYPE, cmd_name: str):
    """Affiche l'aide détaillée pour une commande spécifique."""

    # Nettoyage du nom de la commande (ex: 'add_watch' au lieu de '/add_watch')
    cmd_name = cmd_name.lstrip('/').lower()

    info = COMMAND_INFO.get(cmd_name)

    if not info:
        await update.message.reply_text(
            f"⚠️ Commande `/{cmd_name}` non trouvée. Utilisez `/help` pour la liste complète.")
        return

    message = f"📚 **Aide Détaillée : /{cmd_name}** 📚\n"
    message += f"**Usage :** `{info['usage']}`\n"
    message += f"**Description :** {info['long_desc']}"

    await update.message.reply_text(message, parse_mode='Markdown')


async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Point d'entrée principal pour la commande /help.
    """
    if not context.args:
        # Cas 1: /help sans argument -> Aide générale
        await _send_general_help(update, context)
    else:
        # Cas 2: /help <nom_commande> -> Aide détaillée
        cmd_name = context.args[0]
        await _send_detailed_help(update, context, cmd_name)

# Note: La commande /help ne nécessite pas de protection par whitelist_required
# car elle doit être accessible par tous, y compris les non-admins, pour savoir
# comment s'ajouter à la whitelist.
# Nous l'attacherons directement dans bot/handler.py.