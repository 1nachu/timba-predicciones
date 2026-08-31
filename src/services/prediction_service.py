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
from web.cache import cache

logger = logging.getLogger(__name__)

DASHBOARD_CACHE_PATH = os.path.join(PROJECT_ROOT, 'data', 'dashboard_cache.json')
TZ_ARGENTINA = timezone(timedelta(hours=-3))


@cache.memoize(timeout=3600)
def cargar_datos_liga_cached(liga_id: int) -> Tuple[Dict, float, float, List[str]]:
    """Carga desde BD local (con fallback a CSV) y calcula fuerzas. Memoizado: 1h."""
    liga_info = LIGAS.get(liga_id)
    if not liga_info:
        return {}, 0.0, 0.0, []

    codigo = liga_info.get('codigo')
    url = liga_info.get('url')
    if not codigo and not url:
        return {}, 0.0, 0.0, []

    try:
        df = _get_cached_historical_data(codigo or 'ALL', 3, url or '')
        if df is None or df.empty:
            return {}, 0.0, 0.0, []
        fuerzas, media_local, media_vis = calcular_fuerzas(df)
        equipos = sorted(list(fuerzas.keys()))
        return fuerzas, media_local, media_vis, equipos
    except Exception as e:
        logger.error(f"Error en cargar_datos_liga_cached para liga {liga_id}: {e}")
        return {}, 0.0, 0.0, []


@cache.memoize(timeout=1800)
def obtener_fixtures_cached(liga_id: int) -> List[Dict]:
    """Obtiene próximos partidos cacheados por 30 minutos."""
    fixture_data = URLS_FIXTURE.get(liga_id, {})
    url_fixture = fixture_data.get('url')
    if not url_fixture:
        return []
    try:
        return obtener_proximos_partidos(url_fixture)
    except Exception as e:
        logger.error(f"Error en obtener_fixtures_cached para liga {liga_id}: {e}")
        return []


@cache.memoize(timeout=3600)
def predecir_partido_cached(liga_id: int, local_nombre: str, visitante_nombre: str) -> Optional[Dict]:
    """Calcula y cachea la predicción entre dos equipos por 1 hora."""
    if liga_id == 8:
        cache_todas = {
            lid: cargar_datos_liga_cached(lid)
            for lid in LIGAS
            if LIGAS[lid].get('url') is not None
        }
        return predecir_partido_champions(local_nombre, visitante_nombre, cache_todas)

    fuerzas, media_local, media_vis, equipos_validos = cargar_datos_liga_cached(liga_id)
    if not fuerzas or not equipos_validos:
        return None

    try:
        local_match = emparejar_equipo(local_nombre, equipos_validos)
        vis_match = emparejar_equipo(visitante_nombre, equipos_validos)
        if local_match in fuerzas and vis_match in fuerzas:
            return predecir_partido(local_match, vis_match, fuerzas, media_local, media_vis)
    except Exception as e:
        logger.error(f"Error en predecir_partido_cached ({local_nombre} vs {visitante_nombre}): {e}")
    return None


def cargar_datos_liga(liga_id: int):
    """Wrapper de conveniencia."""
    fuerzas, media_local, media_vis, equipos = cargar_datos_liga_cached(liga_id)
    return None, fuerzas, media_local, media_vis, equipos


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
        if isinstance(data, dict):
            # Normalizar claves int
            if 'partidos_hoy' in data and isinstance(data['partidos_hoy'], dict):
                data['partidos_hoy'] = {
                    int(k) if str(k).isdigit() else k: v
                    for k, v in data['partidos_hoy'].items()
                }
            if 'ligas' in data and isinstance(data['ligas'], dict):
                data['ligas'] = {
                    int(k) if str(k).isdigit() else k: v
                    for k, v in data['ligas'].items()
                }
            return data
    except Exception as e:
        logger.error(f"Error leyendo dashboard_cache.json: {e}")
    return None


def obtener_last_update() -> str:
    """
    Obtiene la fecha/hora de última actualización formateada en hora argentina o texto legible.
    """
    try:
        if os.path.exists(DASHBOARD_CACHE_PATH):
            mtime = os.path.getmtime(DASHBOARD_CACHE_PATH)
            dt_modificacion = datetime.fromtimestamp(mtime)
            ahora = datetime.now()
            delta = ahora - dt_modificacion
            minutos = int(delta.total_seconds() / 60)
            if minutos < 1:
                return "hace menos de 1 minuto"
            elif minutos == 1:
                return "hace 1 minuto"
            elif minutos < 60:
                return f"hace {minutos} minutos"
            else:
                horas = minutos // 60
                return f"hace {horas} hora" if horas == 1 else f"hace {horas} horas"
    except Exception:
        pass
    return "desconocido"
