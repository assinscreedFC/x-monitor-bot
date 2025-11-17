import os
import time
import random
import logging
from playwright.sync_api import sync_playwright
from pathlib import Path
import shutil
import json

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent
# On utilise le dossier de profil PERSISTANT que Docker réutilisera
PLAYWRIGHT_PROFILE_DIR = BASE_DIR / "my_playwright_profile"
TARGET_URL_SETUP = "https://x.com/login"  # Utiliser la page de login de X/Twitter
# ---------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger('Setup')


def setup_playwright_session():
    """
    Lance le navigateur CHROMIUM (visible) pour que l'utilisateur
    se connecte manuellement. Le profil persistant est sauvegardé.
    """
    logger.info(f"Utilisation du dossier de profil Playwright: {PLAYWRIGHT_PROFILE_DIR}")

    # On s'assure qu'il existe
    os.makedirs(PLAYWRIGHT_PROFILE_DIR, exist_ok=True)

    # Suppression de l'ancienne session.json si elle existe pour un clean start
    session_file = BASE_DIR / "storage" / "session.json"
    if os.path.exists(session_file):
        os.remove(session_file)

    with sync_playwright() as p:
        logger.info("Lancement de Chromium (non-headless)...")
        try:
            # --- ARGUMENTS UTILISATEUR RÉINTRODUITS ---
            context = p.chromium.launch_persistent_context(
                user_data_dir=PLAYWRIGHT_PROFILE_DIR,
                headless=False,  # Visible pour la connexion
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--disable-features=IsolateOrigins,site-per-process"
                ],
            )
            # --- FIN ARGUMENTS UTILISATEUR ---
        except Exception as e:
            logger.error(f"Erreur au lancement de Chromium: {e}")
            return

        page = context.new_page()
        page.goto(TARGET_URL_SETUP, timeout=60000)

        logger.info("=" * 50)
        logger.info("➡️ ACTION REQUISE ⬅️")
        logger.info("1. Connecte-toi manuellement à X/Twitter DANS CETTE FENÊTRE.")
        logger.info("2. Une fois connecté (tu vois le fil d'actualité), reviens ici et APPUIE SUR ENTRÉE.")
        logger.info("=" * 50)
        input()  # Pause

        logger.info("Saisie reçue. Le profil est sauvegardé.")

        # Le profil est déjà sauvegardé par context.close() car c'est un contexte persistant

        # --- Étape additionnelle : Vérification et Exportation (Meilleure pratique) ---
        # 1. Récupérer l'état de la session (cookies, local storage)
        storage_state = context.storage_state()

        # 2. Sauvegarder dans le fichier storage/session.json pour que le bot l'utilise
        with open(session_file, "w") as f:
            json.dump(storage_state, f)

        logger.info(f"✅ Fichier de session exporté vers : {session_file}")
        # --- FIN Étape additionnelle ---

        browser = context.browser
        browser.close()
        logger.info("Fermeture du navigateur.")


if __name__ == "__main__":
    setup_playwright_session()