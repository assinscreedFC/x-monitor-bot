FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .

# On installe les paquets Python
RUN pip install --no-cache-dir -r requirements.txt

# --- Installation Playwright V4 (Liste manuelle des dépendances pour Debian 12) ---
# 1. Mettre à jour le catalogue
RUN apt-get update \
    # 2. Installer MANUELLEMENT toutes les dépendances dont Chromium a besoin
    && apt-get install -y \
    xvfb \
    xauth \
    # Installation des polices (Indispensable pour que X.com ne détecte pas le bot)
    fonts-freefont-ttf \
    fonts-noto-color-emoji \
    fonts-roboto \
    libcups2 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxkbcommon0 \
    libasound2 \
    libgdk-pixbuf-2.0-0 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libcairo2 \
    # 3. Installer SEULEMENT le navigateur Chromium
    && playwright install chromium \
    # 4. Nettoyer le cache
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY . .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# 6. Définir l'entrypoint (C'est ce script qui sera lancé au démarrage)
ENTRYPOINT ["./entrypoint.sh"]
CMD ["python","main.py"]