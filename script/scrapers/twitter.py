import asyncio
import random
import logging
from playwright.async_api import async_playwright, Page, BrowserContext, Playwright
from typing import List, Dict, Set, Tuple
from config import settings
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

# On utilise le logger global
logger = logging.getLogger('TelegramBot')

# Dossier local pour screenshots
SCREENSHOTS_DIR = Path.cwd() / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Zone Info pour comparer les dates (X utilise UTC)
UTC = ZoneInfo("UTC")


# --- UTILITAIRES ---

async def human_delay(a=0.5, b=1.5):
    await asyncio.sleep(random.uniform(a, b))


async def _save_screenshot_safe(page: Page, prefix: str, username: str = "unknown") -> str:
    """
    Essaie de prendre une capture d'écran et retourne le chemin (ou une chaîne vide si échec).
    """
    try:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        filename = f"{username}_{prefix}_{timestamp}.png"
        path = SCREENSHOTS_DIR / filename
        await page.screenshot(path=str(path), full_page=True)
        logger.info(f"[Screenshot] Sauvegardé: {path}")
        return str(path)
    except Exception as e:
        logger.error(f"[Screenshot] Échec lors de la capture ({prefix}): {e}")
        return ""


async def smooth_scroll(page: Page, distance: int = 3000, steps: int = 15, delay_min: float = 0.1,
                        delay_max: float = 0.3):
    """
    NOUVEAU: Simule un scroll humain doux au lieu d'un 'wheel' instantané.
    """
    scroll_step = distance // steps
    try:
        for _ in range(steps):
            await page.evaluate(f"window.scrollBy(0, {scroll_step})")
            await asyncio.sleep(random.uniform(delay_min, delay_max))
    except Exception as e:
        logger.warning(f"[Scroll] Erreur pendant le smooth_scroll: {e}")


# --- LOGIQUE D'EXTRACTION (AVEC FILTRE AUTEUR) ---

async def extract_visible_tweets(page: Page, seen_ids: Set[str], username: str, last_seen_date: datetime = None) -> \
Tuple[
    List[Dict], bool]:
    """
    Extrait les tweets visibles et les filtre par date de publication ET par auteur.
    Retourne (liste_des_nouveaux_tweets, y_a-t-il_eu_un_ancien_tweet_vu)
    """
    tweets = []
    found_oldest_tweet = False

    try:
        articles = await page.query_selector_all('article')
    except Exception as e:
        logger.warning(f"Sélecteur 'article' non trouvé ou page fermée: {e}")
        try:
            await _save_screenshot_safe(page, "extract_selector_error", username)
        except Exception:
            pass
        return [], False

    for idx, article in enumerate(articles):
        try:
            # Extraction du contenu
            tweet_texts = await article.query_selector_all('div[lang]')
            tweet_parts = []
            for part in tweet_texts:
                try:
                    txt = await part.inner_text()
                    if txt:
                        tweet_parts.append(txt)
                except Exception:
                    logger.debug(f"inner_text failed on part #{idx}")
            tweet = " ".join(tweet_parts).strip()

            date_el = await article.query_selector("time")
            date_str = await date_el.get_attribute("datetime") if date_el else None

            if date_str:
                post_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                continue

            link_el = await article.query_selector('a[href*="/status/"]')

            # --- CORRECTION 1: VÉRIFICATION DE L'AUTEUR ---
            href = await link_el.get_attribute("href") if link_el else None

            if not href:
                # logger.debug(f"Article {idx} ignoré (pas de lien status, prob. 'suggéré')")
                continue  # Ignore les articles sans lien (pubs, "who to follow", etc.)

            try:
                # Le href est au format "/auteur_du_tweet/status/..."
                tweet_author = href.split('/')[1]
                if tweet_author.lower() != username.lower():
                    # logger.debug(f"Article {idx} ignoré (auteur @{tweet_author} != @{username})")
                    continue  # C'est un tweet "suggéré" ou une pub
            except IndexError:
                # logger.debug(f"Article {idx} ignoré (format lien href étrange: {href})")
                continue
            # --- FIN VÉRIFICATION AUTEUR ---

            link = "https://x.com" + href
            tweet_id = link.split("/")[-1] if link else None

            if not tweet_id or not tweet:
                continue

            # --- LOGIQUE DE FILTRAGE PAR DATE ---
            if last_seen_date:
                if post_date <= last_seen_date:
                    found_oldest_tweet = True
                    break

            if tweet_id not in seen_ids:
                tweets.append({
                    "id": tweet_id,
                    "text": tweet,
                    "date_str": date_str,
                    "date_obj": post_date,
                    "url": link
                })
                seen_ids.add(tweet_id)

        except Exception as e:
            logger.error(f"Erreur extraction tweet #{idx}: {e}", exc_info=False)
            await _save_screenshot_safe(page, f"extract_error_{idx}", username)

    return tweets, found_oldest_tweet


# --- FONCTION PRINCIPALE DE SCRAPING ---

async def fetch_new_posts(p: Playwright, username: str, profile_path: str, last_seen_id: str = None,
                          max_scrolls: int = 6, proxy: Dict = None) -> List[Dict]:
    """
    Fonction principale de scraping, utilisant la date de publication comme ID de suivi.
    """

    last_seen_date = None
    if last_seen_id and last_seen_id != "INIT":
        try:
            last_seen_date = datetime.fromisoformat(last_seen_id.replace('Z', '+00:00'))
        except ValueError:
            logger.error(f"ID de date invalide dans la DB: {last_seen_id}. Reprendra l'historique complet.")
            last_seen_date = None

    tweets_collected = []
    seen_ids = set()
    target_url = f"https://x.com/{username}"
    browser = None
    page = None

    is_init_run = (last_seen_id == "INIT" or last_seen_id is None)
    scroll_limit = 1 if is_init_run else max_scrolls

    try:
        logger.info(f'proxy: {proxy}')
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile_path,
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--start-maximized"
            ],
            proxy=proxy,
        )
        page = await browser.new_page()

        # Action 1: Navigation
        try:
            await page.goto(target_url, timeout=200000, wait_until="networkidle")
            await _save_screenshot_safe(page, "debug_1_after_goto", username)  # DEBUG SCREENSHOT
        except Exception as e:
            logger.error(f"[Scraper] Erreur lors du goto({target_url}): {e}")
            await _save_screenshot_safe(page, "error_goto", username)
            await browser.close()
            return []

        # Action 2: Attente des articles
        try:
            await page.wait_for_selector("article", timeout=200000)
            logger.info(f"[Scraper] Page @{username} chargée, articles détectés.")
            await _save_screenshot_safe(page, "debug_2_after_wait_article", username)  # DEBUG SCREENSHOT
        except Exception as e:
            logger.error(f"[Scraper] @{username}: Page non chargée ou session invalide: {e}")
            await _save_screenshot_safe(page, "error_no_articles", username)
            await browser.close()
            return []

        current_url = page.url

        # --- CORRECTION 2: VÉRIFICATION DE REDIRECTION SILENCIEUSE ---
        if f"/{username.lower()}" not in current_url.lower():
            logger.critical(
                f"[Scraper] @{username}: Redirection silencieuse détectée ! "
                f"Attendait '{username}' mais l'URL est '{current_url}'. Session probablement limitée."
            )
            await _save_screenshot_safe(page, "error_silent_redirect", username)
            await browser.close()
            return []
        # --- FIN DE LA VÉRIFICATION ---

        # Action 3: Vérification de redirection vers Login
        if "login" in current_url or "auth/login" in current_url:
            logger.critical(
                f"[Scraper] Session invalide. Redirigé vers le login ({current_url}). Relancez setup_session.py.")
            await _save_screenshot_safe(page, "error_redirected_to_login", username)
            await browser.close()
            return []

        logger.info(f"[Scraper] Début scroll @{username} (limite: {scroll_limit}, depuis: {last_seen_id or 'INIT'})")

        for scroll in range(scroll_limit):
            # Action 4: Avant extraction
            await _save_screenshot_safe(page, f"debug_scroll_{scroll}_A_before_extract", username)  # DEBUG SCREENSHOT

            new_tweets, found_last = await extract_visible_tweets(page, seen_ids, username, last_seen_date)
            tweets_collected.extend(new_tweets)

            # Action 5: Après extraction
            await _save_screenshot_safe(page, f"debug_scroll_{scroll}_B_after_extract", username)  # DEBUG SCREENSHOT

            if found_last and not is_init_run:
                logger.info(f"[Scraper] @{username}: Tâche terminée (ancien tweet trouvé).")
                break

            if scroll == scroll_limit - 1:
                logger.warning(
                    f"[Scraper] @{username}: Limite de scroll atteinte ({scroll_limit}) pour ce cycle.")

            # Action 6: Clic "Show more"
            buttons = await page.query_selector_all('text="Show more"')
            for idx_b, button in enumerate(buttons):
                try:
                    await button.click()
                    await _save_screenshot_safe(page, f"debug_scroll_{scroll}_C_click_showmore_{idx_b}",
                                                username)  # DEBUG SCREENSHOT
                    await human_delay(0.5, 1.0)
                except Exception as e:
                    logger.debug(f"Échec click Show more #{idx_b}: {e}")
                    await _save_screenshot_safe(page, f"error_showmore_failed_{idx_b}", username)

            # Action 7: Scroll (lent)
            await smooth_scroll(page, distance=3000, steps=10)  # <-- NOUVEAU SCROLL LENT
            await _save_screenshot_safe(page, f"debug_scroll_{scroll}_D_after_scroll", username)  # DEBUG SCREENSHOT

            await human_delay(1.5, 2.5)  # Délai post-scroll

        # Action 8: Fin de boucle
        if not tweets_collected:
            logger.info(f"[Scraper] @{username}: Aucun tweet collecté pendant ce cycle.")
            await _save_screenshot_safe(page, "debug_empty_cycle", username)

        await _save_screenshot_safe(page, "debug_final_before_close", username)  # DEBUG SCREENSHOT
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
        try:
            if page and not page.is_closed():
                await _save_screenshot_safe(page, "error_major_exception", username)
        except Exception:
            pass
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        return []