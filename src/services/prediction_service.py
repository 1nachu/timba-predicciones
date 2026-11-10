"""
Prediction Service
==================
Servicio de caché (con Stale-While-Revalidate), precalentamiento y ejecución de predicciones
por liga y partidos individuales.
Totalmente desacoplado para funcionar tanto en Flask como en Telegram Bot, CLI y background tasks.
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timezone, timedelta
from functools import wraps
from typing import Dict, List, Optional, Tuple, Any, Set

from utils.shared import DB_PATH, PROJECT_ROOT, emparejar_equipo
from timba_core import (
    LIGAS,
    URLS_FIXTURE,
    CSV_A_LIGA_ID,
    CHAMPIONS_EQUIPO_LIGA,
    predecir_partido,
    predecir_partido_champions,
    calcular_fuerzas,
    obtener_proximos_partidos,
    _get_cached_historical_data
)

logger = logging.getLogger(__name__)

DASHBOARD_CACHE_PATH = os.path.join(PROJECT_ROOT, 'data', 'dashboard_cache.json')
TZ_ARGENTINA = timezone(timedelta(hours=-3))


# ============================================================
# CACHÉ EN MEMORIA CON TTL Y STALE-WHILE-REVALIDATE (SWR)
# ============================================================
def ttl_cache(max_age_seconds: int = 3600, stale_while_revalidate: bool = True):
    """
    Decorador de caché en memoria con tiempo de vida (TTL) thread-safe y soporte
    Stale-While-Revalidate (SWR): si existe un valor previo expirado, lo retorna
    de inmediato y lanza la revalidación en un hilo de fondo sin bloquear la petición.
    """
    def decorator(func):
        cache_store: Dict[Any, Tuple[Any, float]] = {}
        revalidating_keys: Set[Any] = set()
        lock = threading.Lock()

        def _revalidate_in_bg(key, args, kwargs):
            try:
                res = func(*args, **kwargs)
                with lock:
                    cache_store[key] = (res, time.time())
            except Exception as e:
                logger.debug(f"Error revalidando caché en background para {func.__name__}: {e}")
            finally:
                with lock:
                    revalidating_keys.discard(key)

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()

            with lock:
                if key in cache_store:
                    val, timestamp = cache_store[key]
                    if now - timestamp < max_age_seconds:
                        return val
                    if stale_while_revalidate:
                        if key not in revalidating_keys:
                            revalidating_keys.add(key)
                            threading.Thread(
                                target=_revalidate_in_bg,
                                args=(key, args, kwargs),
                                daemon=True
                            ).start()
                        return val

            res = func(*args, **kwargs)

            with lock:
                cache_store[key] = (res, time.time())
            return res

        wrapper.cache_clear = lambda: cache_store.clear()
        return wrapper
    return decorator


@ttl_cache(max_age_seconds=3600)
def cargar_datos_liga_cached(liga_id: int) -> Tuple[Dict, float, float, List[str]]:
    """Carga desde BD local (con fallback a CSV) y calcula fuerzas. Memoizado: 1h + SWR."""
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


@ttl_cache(max_age_seconds=1800)
def obtener_fixtures_cached(liga_id: int) -> List[Dict]:
    """Obtiene próximos partidos cacheados por 30 minutos con SWR."""
    fixture_data = URLS_FIXTURE.get(liga_id, {})
    url_fixture = fixture_data.get('url')
    if not url_fixture:
        return []
    try:
        return obtener_proximos_partidos(url_fixture)
    except Exception as e:
        logger.error(f"Error en obtener_fixtures_cached para liga {liga_id}: {e}")
        return []


@ttl_cache(max_age_seconds=3600)
def predecir_partido_cached(liga_id: int, local_nombre: str, visitante_nombre: str) -> Optional[Dict]:
    """Calcula y cachea la predicción entre dos equipos por 1 hora con SWR."""
    # 1. Champions League (Inter-Liga): cargar solo las ligas domésticas de ambos equipos
    if liga_id == 8:
        equipos_champions = list(CHAMPIONS_EQUIPO_LIGA.keys())
        key_local = emparejar_equipo(local_nombre, equipos_champions) if equipos_champions else local_nombre
        key_vis = emparejar_equipo(visitante_nombre, equipos_champions) if equipos_champions else visitante_nombre
        lid_loc = CSV_A_LIGA_ID.get(CHAMPIONS_EQUIPO_LIGA.get(key_local, ''))
        lid_vis = CSV_A_LIGA_ID.get(CHAMPIONS_EQUIPO_LIGA.get(key_vis, ''))

        ligas_a_cargar = {lid for lid in (lid_loc, lid_vis) if lid and lid in LIGAS}
        if not ligas_a_cargar:
            ligas_a_cargar = {lid for lid in LIGAS if LIGAS[lid].get('url') and lid != 10}

        cache_todas = {
            lid: cargar_datos_liga_cached(lid)
            for lid in ligas_a_cargar
        }
        return predecir_partido_champions(local_nombre, visitante_nombre, cache_todas)

    # 2. Ligas Domésticas
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


def obtener_equipos_liga(liga_id: int) -> List[str]:
    """Obtiene la lista ordenada de equipos válidos para una liga (incluye Champions League)."""
    if liga_id == 8:
        return sorted(list(CHAMPIONS_EQUIPO_LIGA.keys()))
    _, _, _, equipos = cargar_datos_liga_cached(liga_id)
    return equipos


def predecir_manual(
    liga_id: int,
    local: str,
    visitante: str
) -> Tuple[Optional[Dict], List[Dict[str, str]], str, str]:
    """
    Ejecuta predicción manual normalizando nombres de equipos, usando caché en memoria
    y retornando avisos estructurados.
    Returns:
        Tuple[prediction_dict, avisos, local_normalizado, visitante_normalizado]
    """
    avisos: List[Dict[str, str]] = []
    if liga_id == 8:
        equipos_champions = list(CHAMPIONS_EQUIPO_LIGA.keys())
        local_norm = emparejar_equipo(local, equipos_champions) if equipos_champions else local
        vis_norm = emparejar_equipo(visitante, equipos_champions) if equipos_champions else visitante
        if local_norm != local:
            avisos.append({'nivel': 'info', 'mensaje': f"'{local}' normalizado a '{local_norm}'"})
        if vis_norm != visitante:
            avisos.append({'nivel': 'info', 'mensaje': f"'{visitante}' normalizado a '{vis_norm}'"})
        pred = predecir_partido_cached(liga_id, local_norm, vis_norm)
        if not pred:
            avisos.append({'nivel': 'danger', 'mensaje': 'No se pudo generar predicción para Champions League.'})
        return pred, avisos, local_norm, vis_norm

    fuerzas, _, _, equipos_validos = cargar_datos_liga_cached(liga_id)
    if not equipos_validos or not fuerzas:
        avisos.append({'nivel': 'danger', 'mensaje': 'No hay datos de equipos disponibles para esta liga.'})
        return None, avisos, local, visitante

    local_norm = emparejar_equipo(local, equipos_validos)
    vis_norm = emparejar_equipo(visitante, equipos_validos)

    if local_norm not in fuerzas or vis_norm not in fuerzas:
        errores = []
        if local_norm not in fuerzas:
            errores.append(f"'{local}' → no encontrado (intenté: '{local_norm}')")
        if vis_norm not in fuerzas:
            errores.append(f"'{visitante}' → no encontrado (intenté: '{vis_norm}')")
        avisos.append({'nivel': 'danger', 'mensaje': f"Equipos no encontrados en BD: {', '.join(errores)}"})
        return None, avisos, local, visitante

    if local_norm != local:
        avisos.append({'nivel': 'info', 'mensaje': f"'{local}' normalizado a '{local_norm}'"})
    if vis_norm != visitante:
        avisos.append({'nivel': 'info', 'mensaje': f"'{visitante}' normalizado a '{vis_norm}'"})

    pred = predecir_partido_cached(liga_id, local_norm, vis_norm)
    return pred, avisos, local_norm, vis_norm


_warmup_started = False
_warmup_lock = threading.Lock()
_dashboard_mem_cache: Dict[str, Any] = {'mtime': None, 'data': None}


def warmup_caches_async() -> None:
    """
    Precalienta en segundo plano las fuerzas de las ligas desde SQLite y los fixtures
    para eliminar el tiempo de carga en frío en la primera petición.
    """
    global _warmup_started
    with _warmup_lock:
        if _warmup_started:
            return
        _warmup_started = True

    def _worker():
        try:
            # Precalentar ligas con datos en SQLite (<150ms total, sin peticiones HTTP)
            for lid in sorted(LIGAS.keys()):
                if LIGAS[lid].get('url') and lid != 10:
                    cargar_datos_liga_cached(lid)
        except Exception as e:
            logger.debug(f"Warmup de fuerzas finalizado con aviso: {e}")

    threading.Thread(target=_worker, daemon=True).start()


def cargar_dashboard_cache() -> Optional[dict]:
    """
    Lee el archivo dashboard_cache.json generado por background_updater,
    memoizando el JSON parseado en memoria según el mtime del archivo.
    Returns: Dict con los datos o None si no existe/está corrupto.
    """
    if not os.path.exists(DASHBOARD_CACHE_PATH):
        return None
    try:
        mtime = os.path.getmtime(DASHBOARD_CACHE_PATH)
        if _dashboard_mem_cache['mtime'] == mtime and _dashboard_mem_cache['data'] is not None:
            return _dashboard_mem_cache['data']

        with open(DASHBOARD_CACHE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
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
            _dashboard_mem_cache['mtime'] = mtime
            _dashboard_mem_cache['data'] = data
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
