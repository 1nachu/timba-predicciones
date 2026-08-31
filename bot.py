#!/usr/bin/env python3
"""
Timba Predictor - Telegram Bot Runner
======================================
Inicia el bot de Telegram con interacción completa:
- Predicciones Pre-Match
- Predicciones In-Play Dinámicas (En Vivo)
- Fixtures del día
- Value Bets (+EV)
- Teclados interactivos y menús inline

Uso:
    python bot.py
"""

import sys
import os
import logging

# Inyectar 'src/' al sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from bot.bot_app import run_telegram_bot

# Configuración de Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("timba_telegram_bot")

if __name__ == "__main__":
    run_telegram_bot()
