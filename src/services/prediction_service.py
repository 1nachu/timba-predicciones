"""
Prediction Service
==================
Servicio de caché y ejecución de predicciones por liga y partidos individuales.
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from utils.shared import DB_PATH, PROJECT_ROOT, emparejar_equipo
from timba_core import (
    LIGAS,
    URLS_FIXTURE,
    predecir_partido,
    predecir_partido_champions,
    calcular_fuerzas,
    obtener_proximos_partidos,
    _get_cached_historical_data
)

logger = logging.getLogger(__name__)

DASHBOARD_CACHE_PATH = os.path.join(PROJECT_ROOT, 'data', 'dashboard_cache.json')
TZ_ARGENTINA = timezone(timedelta(hours=-3))


def cargar_dashboard_cache() -> Optional[dict]:
    """
    Lee el archivo dashboard_cache.json generado por background_updater.
    Returns: Dict con los datos o None si no existe/está corrupto.
    """
    if not os.path.exists(DASHBOARD_CACHE_PATH):
        return None
    try:
        with open(DASHBOARD_CACHE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get('partidos_por_liga') is not None:
            return data
    except Exception as e:
        logger.error(f"Error leyendo dashboard_cache.json: {e}")
    return None


def obtener_last_update() -> str:
    """
    Obtiene la fecha/hora de última actualización formateada en hora argentina.
    """
    cache_data = cargar_dashboard_cache()
    if cache_data and cache_data.get('timestamp'):
        try:
            dt = datetime.fromisoformat(cache_data['timestamp'])
            return dt.strftime('%d/%m/%Y %H:%M')
        except Exception:
            pass
    if os.path.exists(DASHBOARD_CACHE_PATH):
        try:
            mtime = os.path.getmtime(DASHBOARD_CACHE_PATH)
            dt = datetime.fromtimestamp(mtime, tz=TZ_ARGENTINA)
            return dt.strftime('%d/%m/%Y %H:%M')
        except Exception:
            pass
    return datetime.now(TZ_ARGENTINA).strftime('%d/%m/%Y %H:%M')
