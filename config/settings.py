import os
import logging
import sys
from pathlib import Path

# --- Chemins de base ---

# Définit le répertoire racine du projet (le dossier 'project_root')
# /app dans notre conteneur Docker
BASE_DIR = Path(__file__).resolve().parent.parent

# Définit les chemins vers les dossiers importants
STORAGE_DIR = BASE_DIR / "storage"
LOGS_DIR = BASE_DIR / "logs"

# Crée le dossier de logs s'il n'existe pas (utile pour Docker)
LOGS_DIR.mkdir(exist_ok=True)


# --- Variables d'environnement (.env) ---

# 1. Token du Bot (Obligatoire)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    # Si le token n'est pas trouvé, on arrête tout.
    logging.critical("TELEGRAM_BOT_TOKEN n'est pas défini dans .env !")
    sys.exit("Erreur: TELEGRAM_BOT_TOKEN n'est pas défini.")

# 2. Nombre de workers (scrapers parallèles)
try:
    WORKER_COUNT = int(os.getenv('WORKER_COUNT', 4))
except ValueError:
    logging.warning("WORKER_COUNT invalide, utilisation de la valeur par défaut (4)")
    WORKER_COUNT = 4

# 3. Réglage des liens par défaut
INCLUDE_LINKS_DEFAULT = os.getenv('INCLUDE_LINKS_DEFAULT', 'on').lower() == 'on'

# 4. Fuseau horaire
TZ = os.getenv('TZ', 'Europe/Paris')
os.environ['TZ'] = TZ

# --- AJOUTS CORRIGÉS : Identifiants X/Twitter ---
X_USERNAME = os.getenv('X_USERNAME')
X_PASSWORD = os.getenv('X_PASSWORD')

if not X_USERNAME or not X_PASSWORD:
    logging.warning("X_USERNAME ou X_PASSWORD ne sont pas définis. Le login automatique échouera si la session est invalide.")
# --- FIN AJOUTS CORRIGÉS ---


# --- Fichiers de stockage (JSON) ---
MONITORS_FILE = "monitors.json"
WHITELIST_FILE = "whitelist.json"
PROXIES_FILE = "proxies.json"
SETTINGS_FILE = "settings.json"


# --- Constantes du Scheduler ---
MIN_WAIT_SECONDS = 3 * 60  # 180 secondes
MAX_WAIT_SECONDS = 6 * 60  # 360 secondes


# --- Configuration du Logging ---
LOG_FILE_PATH = LOGS_DIR / "bot.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# On crée un logger spécifique pour notre app
logger = logging.getLogger('TelegramBot')
logger.info(f"Configuration chargée. {WORKER_COUNT} workers configurés.")
logger.info(f"Chemin stockage: {STORAGE_DIR}, Chemin logs: {LOGS_DIR}")