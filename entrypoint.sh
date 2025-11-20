#!/bin/bash

# 1. Démarrer Xvfb en arrière-plan sur le display :99
Xvfb :99 -screen 0 1920x1080x24 &

# 2. Exporter la variable DISPLAY pour que tout le monde la voie
export DISPLAY=:99

# 3. Attendre un peu que Xvfb soit prêt
sleep 2

# 4. Lancer le bot Python
exec python main.py