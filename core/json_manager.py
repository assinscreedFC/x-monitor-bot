import aiofiles
import asyncio
import json
import os
import logging

# On définit les noms de nos fichiers de "base de données"
MONITORS_FILE = 'monitors.json'
WHITELIST_FILE = 'whitelist.json'
PROXIES_FILE = 'proxies.json'
SETTINGS_FILE = 'settings.json'  # Pour les paramètres dynamiques


class JSONStorageManager:
    """
    Gère l'accès concurrentiel (lecture/écriture) aux fichiers JSON
    en utilisant asyncio.Lock.
    """

    def __init__(self, base_path="storage"):
        self.base_path = base_path

        # Un dictionnaire de verrous, un pour chaque fichier JSON
        # C'est le "feu tricolore" qui empêche les collisions
        self._locks = {
            MONITORS_FILE: asyncio.Lock(),
            WHITELIST_FILE: asyncio.Lock(),
            PROXIES_FILE: asyncio.Lock(),
            SETTINGS_FILE: asyncio.Lock(),
        }

        # S'assurer que le dossier de stockage existe (pour Docker)
        os.makedirs(self.base_path, exist_ok=True)
        # Correction de l'encodage
        logging.info(f"StorageManager initialisé (base: {self.base_path})")

    def _get_path(self, filename: str) -> str:
        """Construit le chemin complet du fichier."""
        return os.path.join(self.base_path, filename)

    async def read_data(self, filename: str) -> list | dict:
        """
        Lit les données d'un fichier JSON de manière asynchrone et sécurisée.
        Retourne une liste ou un dict vide si le fichier est vide ou n'existe pas.
        """
        file_path = self._get_path(filename)
        lock = self._locks.get(filename)

        if not lock:
            # Correction de l'encodage
            logging.error(f"Pas de verrou défini pour {filename}")
            return []

        async with lock:
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    if not content:
                        # Le fichier est vide (créé par le .bat)
                        return [] if filename != SETTINGS_FILE else {}
                    return json.loads(content)
            except FileNotFoundError:
                # Correction de l'encodage
                logging.warning(f"Fichier {filename} non trouvé, retourne data vide.")
                return [] if filename != SETTINGS_FILE else {}
            except json.JSONDecodeError:
                # Correction de l'encodage
                logging.error(f"Erreur de décodage JSON dans {filename}, retourne data vide.")
                return [] if filename != SETTINGS_FILE else {}
            except Exception as e:
                logging.exception(f"Erreur inattendue en lisant {filename}: {e}")
                return [] if filename != SETTINGS_FILE else {}

    async def write_data(self, filename: str, data: list | dict):
        """
        Écrit des données dans un fichier JSON de manière asynchrone et sécurisée.
        """
        file_path = self._get_path(filename)
        lock = self._locks.get(filename)

        if not lock:
            # Correction de l'encodage
            logging.error(f"Pas de verrou défini pour {filename}")
            return

        async with lock:
            try:
                async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                    # indent=2 pour que les fichiers JSON restent lisibles
                    await f.write(json.dumps(data, indent=2))
            except Exception as e:
                logging.exception(f"Erreur en écrivant dans {filename}")


# --- Point important ---
# On crée UNE SEULE instance de ce manager, que l'on importera partout
# C'est un "Singleton"
storage_manager = JSONStorageManager()