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

# --- CONSTANTE D'IDENTITÉ (PC Windows) ---
REAL_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"


# --- NOUVELLE FONCTION DE CAMOUFLAGE ---
async def apply_stealth(page: Page):
    """
    Injecte manuellement du JavaScript pour cacher que c'est un bot.
    """
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: 'granted', onchange: null }) :
                originalQuery(parameters)
        );
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Open Source Technology Center';
            if (parameter === 37446) return 'Mesa DRI Intel(R) HD Graphics 630 (Kaby Lake GT2)';
            return getParameter(parameter);
        };
    """)


# --- UTILITAIRES GÉNÉRAUX ---

async def human_delay(a=0.5, b=1.5):
    await asyncio.sleep(random.uniform(a, b))


async def _save_screenshot_safe(page: Page, prefix: str, username: str = "unknown") -> str:
    try:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        filename = f"{username}_{prefix}_{timestamp}.png"
        path = SCREENSHOTS_DIR / filename
        await page.screenshot(path=str(path), full_page=True)
        logger.info(f"[Screenshot] Sauvegardé: {path}")
        return str(path)
    except Exception as e:
        logger.error(f"[Screenshot] Échec capture ({prefix}): {e}")
        return ""


async def smooth_scroll(page: Page, distance: int = 3000, steps: int = 15, delay_min: float = 0.1,
                        delay_max: float = 0.3):
    scroll_step = distance // steps
    try:
        for _ in range(steps):
            await page.evaluate(f"window.scrollBy(0, {scroll_step})")
            await asyncio.sleep(random.uniform(delay_min, delay_max))
    except Exception as e:
        logger.warning(f"[Scroll] Erreur: {e}")


# --- UTILITAIRES MEDIA (NOUVEAU) ---

def _first_src_from_srcset(srcset: str) -> str:
    if not srcset:
        return ""
    parts = [p.strip() for p in srcset.split(',') if p.strip()]
    if not parts:
        return ""
    # Format habituel: "url 1x, url 2x" -> on prend l'url
    return parts[0].split(' ')[0]


def _is_probably_media_url(url: str) -> bool:
    if not url:
        return False
    u = url.lower()
    media_signals = ['twimg', 'pbs.twimg', '/media/', '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.m3u8']
    return any(s in u for s in media_signals)


async def _collect_media_from_article(article: Page) -> List[str]:
    """
    Récupère URLs des images/vidéos présent dans un <article>.
    Nettoie les URLs Twitter pour avoir la meilleure qualité (.jpg/.png).
    """
    media_urls: List[str] = []

    # 1. Images (src / data-src / srcset)
    try:
        imgs = await article.query_selector_all('img')
        for img in imgs:
            try:
                src = await img.get_attribute('src') or await img.get_attribute('data-src')
                if not src:
                    srcset = await img.get_attribute('srcset') or await img.get_attribute('data-srcset')
                    src = _first_src_from_srcset(srcset)
                if not src:
                    continue

                # Normalisation URL
                if src.startswith("//"):
                    src = "https:" + src
                if src.startswith("/"):
                    src = "https://x.com" + src

                # --- NETTOYAGE SPECIFIQUE TWITTER (Le changement est ici) ---
                if "pbs.twimg.com" in src and "format=" in src:
                    # Exemple: https://pbs.twimg.com/.../XYZ?format=jpg&name=small
                    # On veut: https://pbs.twimg.com/.../XYZ.jpg
                    try:
                        base_url = src.split('?')[0]
                        extension = "jpg"  # par défaut
                        if "format=png" in src:
                            extension = "png"
                        src = f"{base_url}.{extension}"
                    except:
                        pass  # Si échec, on garde l'original
                # ------------------------------------------------------------

                # Filtrage (avatars, emojis, etc.)
                alt = (await img.get_attribute('alt') or "").lower()
                if 'profile_images' in src or 'avatar' in src or 'emoji' in src or 'sprite' in src:
                    continue
                if src.startswith('data:'):
                    continue

                if _is_probably_media_url(src):
                    media_urls.append(src)
            except Exception:
                continue
    except Exception:
        pass

    # 2. Vidéos / Source tags
    try:
        video_tags = await article.query_selector_all('video, source')
        for v in video_tags:
            try:
                vsrc = await v.get_attribute('src') or await v.get_attribute('data-src')
                if not vsrc:
                    continue
                if vsrc.startswith("//"):
                    vsrc = "https:" + vsrc
                if vsrc.startswith("/"):
                    vsrc = "https://x.com" + vsrc

                if _is_probably_media_url(vsrc):
                    media_urls.append(vsrc)
            except Exception:
                continue
    except Exception:
        pass

    # Déduplication en gardant l'ordre
    seen = set()
    unique = []
    for u in media_urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique

# --- LOGIQUE D'EXTRACTION (MISE À JOUR) ---

async def extract_visible_tweets(page: Page, seen_ids: Set[str], username: str, last_seen_date: datetime = None) -> \
        Tuple[List[Dict], bool]:
    tweets = []
    found_oldest_tweet = False

    try:
        articles = await page.query_selector_all('article')
    except Exception as e:
        logger.warning(f"Sélecteur 'article' non trouvé: {e}")
        return [], False

    for idx, article in enumerate(articles):
        try:
            # Extraction du texte
            tweet_texts = await article.query_selector_all('div[lang]')
            tweet_parts = []
            for part in tweet_texts:
                try:
                    txt = await part.inner_text()
                    if txt: tweet_parts.append(txt)
                except:
                    pass
            tweet = " ".join(tweet_parts).strip()

            # Extraction Date
            date_el = await article.query_selector("time")
            date_str = await date_el.get_attribute("datetime") if date_el else None

            if date_str:
                post_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                continue

            # Extraction Lien et ID
            link_el = await article.query_selector('a[href*="/status/"]')

            # Vérification Auteur (Anti-Pub/Recommandation)
            href = await link_el.get_attribute("href") if link_el else None
            if not href: continue

            try:
                tweet_author = href.split('/')[1]
                if tweet_author.lower() != username.lower():
                    continue  # Ignore les tweets qui ne sont pas de l'auteur
            except IndexError:
                continue

            link = "https://x.com" + href
            tweet_id = link.split("/")[-1] if link else None

            # Note: On accepte un tweet même sans texte s'il a des médias
            if not tweet_id:
                continue

            # Logique de date
            if last_seen_date:
                if post_date <= last_seen_date:
                    found_oldest_tweet = True
                    break

            if tweet_id not in seen_ids:
                # --- RECUPERATION DES MEDIAS ---
                media_urls = await _collect_media_from_article(article)

                tweets.append({
                    "id": tweet_id,
                    "text": tweet,
                    "date_str": date_str,
                    "date_obj": post_date,
                    "url": link,
                    "media": media_urls  # Ajout du champ media
                })
                seen_ids.add(tweet_id)

        except Exception as e:
            logger.error(f"Erreur extraction tweet #{idx}: {e}", exc_info=False)

    return tweets, found_oldest_tweet


# --- FONCTION PRINCIPALE ---

async def fetch_new_posts(p: Playwright, username: str, profile_path: str, last_seen_id: str = None,
                          max_scrolls: int = 6, proxy: Dict = None) -> List[Dict]:
    # Conversion de la date
    last_seen_date = None
    if last_seen_id and last_seen_id != "INIT":
        try:
            last_seen_date = datetime.fromisoformat(last_seen_id.replace('Z', '+00:00'))
        except ValueError:
            last_seen_date = None

    tweets_collected = []
    seen_ids = set()
    target_url = f"https://x.com/{username}"
    browser = None
    page = None

    is_init_run = (last_seen_id == "INIT" or last_seen_id is None)
    scroll_limit = 1 if is_init_run else max_scrolls

    try:
        logger.info(f'Lancement scraping pour @{username} avec proxy: {proxy}')

        args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--hide-scrollbars",
            "--mute-audio",
            "--use-gl=swiftshader",
            "--window-size=1920,1080",
        ]

        # 1. Lancement du navigateur avec profil persistant
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=profile_path,
            headless=False,
            args=args,
            proxy=proxy,
            user_agent=REAL_USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            locale="fr-FR",
            timezone_id="Europe/Paris",
            permissions=["geolocation", "notifications"],
        )

        page = await browser.new_page()

        # 2. Application du camouflage (Stealth)
        await apply_stealth(page)

        # 3. Navigation
        try:
            await page.goto(target_url, timeout=90000, wait_until="domcontentloaded")
            await human_delay(2.0, 3.0)

        except Exception as e:
            logger.error(f"[Scraper] Erreur goto({target_url}): {e}")
            await _save_screenshot_safe(page, "error_goto", username)
            await browser.close()
            return []

        # 4. Vérification : Page chargée ?
        try:
            await page.wait_for_selector("article", timeout=60000)
        except Exception as e:
            logger.error(f"[Scraper] @{username}: Pas d'articles trouvés (Timeout).")
            await _save_screenshot_safe(page, "error_no_articles", username)
            await browser.close()
            return []

        # 5. Vérification : Redirection Login ou Erreur ?
        current_url = page.url
        if "login" in current_url or "auth" in current_url:
            logger.critical(f"[Scraper] Redirigé vers Login pour @{username}.")
            await _save_screenshot_safe(page, "error_login_redirect", username)
            await browser.close()
            return []

        # 6. Boucle de Scroll et Extraction
        logger.info(f"[Scraper] Début scroll @{username}")

        for scroll in range(scroll_limit):
            new_tweets, found_last = await extract_visible_tweets(page, seen_ids, username, last_seen_date)
            tweets_collected.extend(new_tweets)

            if found_last and not is_init_run:
                logger.info(f"[Scraper] @{username}: Ancien tweet trouvé, arrêt.")
                break

            # Clic "Show more"
            try:
                buttons = await page.query_selector_all('text="Show more"')
                for btn in buttons:
                    await btn.click()
                    await human_delay(0.5, 1.0)
            except:
                pass

            await smooth_scroll(page, distance=3000, steps=10)
            await human_delay(1.5, 2.5)

        await browser.close()

        # Tri et retour
        tweets_collected.sort(key=lambda t: t['date_obj'])

        if not tweets_collected:
            return []

        if is_init_run:
            return [tweets_collected[-1]]

        return tweets_collected

    except Exception as e:
        logger.exception(f"Erreur majeure scraping @{username}: {e}")
        try:
            if page: await _save_screenshot_safe(page, "error_fatal", username)
            if browser: await browser.close()
        except:
            pass
        return []