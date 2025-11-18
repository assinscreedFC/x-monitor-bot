import os, json, time, random
from pathlib import Path
from playwright.sync_api import sync_playwright
from curl_cffi import requests  # pip install curl-cffi
from http.cookies import SimpleCookie

def human_delay(a=1.2, b=2.5):
    time.sleep(random.uniform(a, b))

# --- CONFIG ---
temp_profile = str(Path.home() / "my_playwright_profile_2")
os.makedirs(temp_profile, exist_ok=True)
target_url = ("https://x.com/")  # ou la page cible où tu veux te connecter
proxy_config = {
    'server': 'http://isp.oxylabs.io:8001',
    'username': 'bibobi_1Qufi',
    'password': 'Bibobibabobi134679+'
}
# ----------------

# Util : transforme la liste de cookies Playwright en header "Cookie"
def build_cookie_header(cookies_list):
    # cookies_list: [{'name':..., 'value':..., 'domain':...}, ...]
    return "; ".join([f"{c['name']}={c['value']}" for c in cookies_list])

# Util : convertit localStorage/sessionStorage str->dict
def parse_storage_json(json_str):
    try:
        return json.loads(json_str)
    except Exception:
        return {}

# --- PHASE PLAYWRIGHT: ouvrir navigateur, laisser login manuellement, récupérer storage ---
with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=temp_profile,
        channel="chrome",
        headless=False,
        args=[
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy=proxy_config
    )

    page = context.new_page()
    # ouvre la page cible pour faciliter la connexion
    page.goto(target_url, wait_until="domcontentloaded")
    print("➡️ Connecte-toi manuellement dans la fenêtre Chrome qui vient de s'ouvrir.")
    input("Appuie sur Entrée une fois connecté et la page principale chargée...")

    # donne un petit temps pour que les JS terminent d'écrire localStorage/cookies
    human_delay(0.5, 1.5)

    # 1) cookies
    cookies = context.cookies()
    print(f"✅ Cookies récupérés: {len(cookies)} items")

    # 2) localStorage
    try:
        local_storage_json = page.evaluate("() => JSON.stringify(window.localStorage)")
        local_storage = parse_storage_json(local_storage_json)
    except Exception:
        local_storage = {}
    print(f"✅ localStorage récupéré: {len(local_storage)} clés")

    # 3) sessionStorage
    try:
        session_storage_json = page.evaluate("() => JSON.stringify(window.sessionStorage)")
        session_storage = parse_storage_json(session_storage_json)
    except Exception:
        session_storage = {}
    print(f"✅ sessionStorage récupéré: {len(session_storage)} clés")

    # 4) storage_state (cookies + localStorage) utile pour sauvegarder
    try:
        storage_state = context.storage_state()  # dict
        state_path = Path(temp_profile) / "storage_state.json"
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(storage_state, f, indent=2)
        print(f"✅ storage_state sauvegardé: {state_path}")
    except Exception as e:
        print("⚠️ Impossible d'extraire storage_state:", e)

    # Exemple: tenter d'extraire tokens connus (adapter en fonction du site)
    # Pour X/Twitter tu peux chercher des clés dans localStorage comme 'gt' ou 'guest_token'
    possible_tokens = {}
    for k in ("guest_token", "gt", "auth_token", "Bearer", "csrf_token", "csrf"):
        if k in local_storage:
            possible_tokens[k] = local_storage[k]
    # parfois un token est injecté par un script variable globale
    try:
        # ATTENTION : évaluer des expressions trop larges peut être risqué ; ici on tente prudemment
        script_token = page.evaluate("() => (window.__INITIAL_STATE__ ? JSON.stringify(window.__INITIAL_STATE__) : null)")
        if script_token:
            possible_tokens["__INITIAL_STATE__"] = "present"
    except Exception:
        pass

    print("✅ tokens potentiels trouvés:", list(possible_tokens.keys()))

    # On garde une copie locale puis ferme proprement
    # Mais on a déjà extrait tout ce dont on a besoin
    context.close()

# --- PHASE cURL_CFFI: préparer la session et faire la requête ---
session = requests.Session()

# 1) injecter cookies
cookie_header = build_cookie_header(cookies)
# curl_cffi.Session accepte session.headers; on place Cookie header manuellement
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Cookie": cookie_header
})

# 2) si on détecte un token CSRF ou guest token, ajoute-le dans les headers appropriés
# Exemple générique:
if "csrf_token" in local_storage:
    session.headers["x-csrf-token"] = local_storage["csrf_token"]
if "guest_token" in local_storage:
    session.headers["x-guest-token"] = local_storage["guest_token"]

# 3) si le site nécessite Authorization: Bearer <token> et qu'on l'a trouvé
if "auth_token" in local_storage:
    session.headers["Authorization"] = f"Bearer {local_storage['auth_token']}"

# 4) faire la requête via le proxy (curl_cffi gère `impersonate` pour simuler un navigateur)
target_api = "https://www.leboncoin.fr/ad/voitures/2997258439"
print("➡️ Requête via curl_cffi vers:", target_api)
resp = session.get(target_api, impersonate="chrome120", proxies={
    "http": proxy_config["server"],
    "https": proxy_config["server"]
}, timeout=30)  # ajuste timeout si nécessaire

print("Status:", resp.status_code)
ct = resp.headers.get("Content-Type", "")
if "application/json" in ct:
    try:
        print("JSON reçu :", resp.json()[:500])
    except Exception:
        print("Erreur parsing JSON")
else:
    # afficher un extrait du HTML
    text = resp.text[:1000]
    print("Contenu (extrait):\n", text)
