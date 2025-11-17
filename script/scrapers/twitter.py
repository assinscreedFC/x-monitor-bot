import asyncio
import random
import logging
from playwright.async_api import async_playwright, Page, BrowserContext, Playwright
from typing import List, Dict, Set
from config import settings
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# On utilise le logger global
logger = logging.getLogger('TelegramBot')
DOCKER_PERSISTENT_PROFILE_PATH = "/app/my_playwright_profile"  # Chemin du profil persistant


# Ton utilitaire, maintenant en async
async def human_delay(a=0.5, b=1.5):  # On réduit le délai en production
    await asyncio.sleep(random.uniform(a, b))


# Zone Info pour comparer les dates (X utilise UTC)
UTC = ZoneInfo("UTC")


async def extract_visible_tweets(page: Page, seen_ids: Set[str], last_seen_date: datetime = None) -> (List[Dict], bool):
    """
    Extrait les tweets visibles et les filtre par date de publication.
    Retourne (liste_des_nouveaux_tweets, y_a-t-il_eu_un_ancien_tweet_vu)
    """
    tweets = []
    found_oldest_tweet = False  # Vrai si on trouve un tweet plus vieux que last_seen_date

    try:
        articles = await page.query_selector_all('article')
    except Exception as e:
        logger.warning(f"Sélecteur 'article' non trouvé ou page fermée: {e}")
        return [], False

    for idx, article in enumerate(articles):
        try:
            # Extraction du contenu
            tweet_texts = await article.query_selector_all('div[lang]')
            tweet = " ".join([await part.inner_text() for part in tweet_texts if part]).strip()

            date_el = await article.query_selector("time")
            date_str = await date_el.get_attribute("datetime") if date_el else None

            if date_str:
                # Assurez-vous que le format est ISO 8601 (ex: 2025-01-01T10:00:00.000Z)
                post_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                continue  # Ignore les articles sans date (publicités, etc.)

            link_el = await article.query_selector('a[href*="/status/"]')
            link = "https://x.com" + await link_el.get_attribute("href") if link_el else None
            tweet_id = link.split("/")[-1] if link else None

            if not tweet_id or not tweet:
                continue

            # --- LOGIQUE DE FILTRAGE PAR DATE ---
            # Si nous avons une date de référence, on filtre.
            if last_seen_date:
                if post_date <= last_seen_date:
                    found_oldest_tweet = True
                    break  # Arrêt immédiat si on trouve un tweet plus vieux ou égal à l'ancien

            # --- FIN LOGIQUE DE FILTRAGE ---

            if tweet_id not in seen_ids:
                # Suppression du filtre de date inutile

                tweets.append({
                    "id": tweet_id,
                    "text": tweet,
                    "date_str": date_str,
                    "date_obj": post_date,  # Ajout de l'objet datetime pour comparaison
                    "url": link
                })
                seen_ids.add(tweet_id)

        except Exception as e:
            logger.error(f"Erreur extraction tweet #{idx}: {e}", exc_info=False)

    return tweets, found_oldest_tweet


async def fetch_new_posts(p: Playwright, username: str, profile_path: str, last_seen_id: str = None,
                          max_scrolls: int = 20, proxy: Dict = None) -> List[Dict]:
    """
    Fonction principale de scraping, utilisant la date de publication comme ID de suivi.
    """

    # Conversion de last_seen_id en datetime
    last_seen_date = None
    if last_seen_id and last_seen_id != "INIT":
        try:
            # On suppose que last_seen_id est stocké sous forme ISO (compatible fromisoformat)
            last_seen_date = datetime.fromisoformat(last_seen_id.replace('Z', '+00:00'))
        except ValueError:
            logger.error(f"ID de date invalide dans la DB: {last_seen_id}. Reprendra l'historique complet.")
            last_seen_date = None

    tweets_collected = []
    seen_ids = set()
    target_url = f"https://x.com/{username}"
    browser = None

    # Logique de Scroll : 1 scroll pour INIT, 2 scrolls pour les runs normaux
    is_init_run = (last_seen_id == "INIT")
    scroll_limit = 2 if not is_init_run else 1

    # Correction de max_scrolls
    if scroll_limit == 2:
        scroll_limit = max_scrolls  # Pour utiliser la valeur passée dans l'argument

    try:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile_path,
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",  # Stealth
                "--disable-gpu",
                "--start-maximized"
            ],
            proxy=proxy,
        )
        page = await browser.new_page()
        await page.goto(target_url, timeout=60000, wait_until="networkidle")

        # Validation de la connexion (reste la même)
        try:
            await page.wait_for_selector("article", timeout=10000)
            logger.info(f"[Scraper] Page @{username} chargée, articles détectés.")
        except Exception as e:
            logger.error(f"[Scraper] @{username}: Page non chargée ou session invalide.")
            await browser.close()
            return []

        # Vérification si on est redirigé vers le login (anti-bot)
        if "login" in page.url or "auth/login" in page.url:
            logger.critical(
                f"[Scraper] Session invalide. Redirigé vers le login. Relancez setup_session.py.")
            await browser.close()
            return []

        logger.info(f"[Scraper] Début scroll @{username} (limite: {scroll_limit}, depuis: {last_seen_id or 'INIT'})")

        for scroll in range(scroll_limit):
            # Suppression du log de screenshot inutile
            new_tweets, found_last = await extract_visible_tweets(page, seen_ids, last_seen_date)
            tweets_collected.extend(new_tweets)

            if found_last and not is_init_run:
                logger.info(f"[Scraper] @{username}: Tâche terminée (ancien tweet trouvé).")
                break

            if scroll == scroll_limit - 1:
                logger.warning(
                    f"[Scraper] @{username}: Limite de scroll atteinte ({scroll_limit}) pour ce cycle.")

            # Logique de scroll
            buttons = await page.query_selector_all('text="Show more"')
            for button in buttons:
                try:
                    await button.click()
                    await human_delay(0.5, 1.0)
                except Exception:
                    pass

            await page.mouse.wheel(0, 3000)
            await human_delay(1.5, 2.5)

        await browser.close()

        # Finalisation et tri
        tweets_collected.sort(key=lambda t: t['date_obj'])

        if not tweets_collected:
            return []

        if is_init_run:
            logger.info(f"[Scraper] @{username}: Run initial. Ne retourne que le tweet le plus récent.")
            return [tweets_collected[-1]]

        return tweets_collected

    except Exception as e:
        logger.exception(f"Erreur majeure lors du scraping de @{username}: {e}")
        if browser:
            await browser.close()
        return []