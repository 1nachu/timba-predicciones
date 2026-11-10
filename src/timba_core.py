"""
Timba Predictor - Core Engine v2.0
===================================

Motor central de análisis y predicción de partidos de fútbol.
Utiliza Distribución de Poisson para calcular probabilidades.

Características:
- Cálculo de fuerzas de ataque/defensa por equipo
- Predicción de resultados 1X2 y mercados (Over/Under, BTTS)
- Integración con bases de datos locales
- Normalización de nombres de equipos vía utils.shared

Autor: Timba Team
Última actualización: Febrero 2026
"""

# ========== IMPORTS ESTÁNDAR ==========
import io
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional, Dict, List, Any

# ========== IMPORTS DE TERCEROS ==========
import pandas as pd
import requests
from dotenv import load_dotenv

# Cargar variables desde .env (si existe)
load_dotenv()

# ========== CONFIGURACIÓN DE LOGGING ==========
logger = logging.getLogger(__name__)

# ========== IMPORTAR MÓDULO CYTHON OPTIMIZADO ==========
try:
    from src.timba_fast import predecir_partido_optimizado
    USE_CYTHON = True
    logger.info("✓ Módulo Cython (timba_fast) cargado correctamente")
except ImportError:
    try:
        from timba_fast import predecir_partido_optimizado
        USE_CYTHON = True
        logger.info("✓ Módulo Cython (timba_fast) cargado correctamente")
    except ImportError:
        USE_CYTHON = False
        logger.debug("Módulo Cython no disponible, usando Python puro")

# ========== IMPORTAR PROVEEDOR DE DATOS ==========
try:
    from db_data_provider import DatabaseDataProvider
    DB_PROVIDER_AVAILABLE = True
    _data_provider = DatabaseDataProvider()
    logger.info("✓ Proveedor de BD inicializado")
except ImportError:
    DB_PROVIDER_AVAILABLE = False
    _data_provider = None
    logger.warning("⚠️  Proveedor de BD no disponible, usando solo CSVs")

# ========== IMPORTAR UTILIDADES COMPARTIDAS ==========
try:
    from utils.shared import (
        get_db_connection,
        normalizar_csv,
        descargar_csv_safe,
        emparejar_equipo,
        encontrar_equipo_similar,
        imprimir_barra,
        ALIAS_TEAMS,
        CHAMPIONS_EQUIPO_LIGA,
        DB_PATH,
        LOGS_DIR,
    )
    from utils.markets import (
        obtener_mejor_recomendacion,
        determinar_prediccion_1x2,
        generar_recomendaciones,
        calcular_semaforo,
        calcular_mercados_adicionales,
        PREDICCION_UMBRAL_GANA,
        PREDICCION_UMBRAL_DOBLE,
    )
except ImportError:
    logger.warning("⚠️  utils.shared no disponible, usando funciones locales")
    from difflib import get_close_matches
    
    ALIAS_TEAMS = {}
    CHAMPIONS_EQUIPO_LIGA = {}
    DB_PATH = Path("data/databases/football_data.db")
    LOGS_DIR = Path("logs")
    
    def normalizar_csv(df):
        df.columns = df.columns.str.strip()
        return df
    
    def emparejar_equipo(nombre_fixture, equipos_validos):
        matches = get_close_matches(nombre_fixture, equipos_validos, n=1, cutoff=0.6)
        return matches[0] if matches else nombre_fixture
    
    def encontrar_equipo_similar(nombre, equipos_validos):
        return get_close_matches(nombre, equipos_validos, n=3, cutoff=0.6)
    
    def imprimir_barra(valor, maximo=100, ancho=25):
        porcentaje = (valor / maximo) * 100 if maximo > 0 else 0
        relleno = int((porcentaje / 100) * ancho)
        barra = '█' * relleno + '░' * (ancho - relleno)
        return f"[{barra}] {porcentaje:.1f}%"
    
    def descargar_csv_safe(url_or_list, timeout=15, usecols=None):
        response = requests.get(url_or_list, timeout=timeout)
        response.raise_for_status()
        return pd.read_csv(io.StringIO(response.text), usecols=usecols)

# ========== DICCIONARIO DE LIGAS Y FIXTURES (CENTRALIZADO) ==========
# Fuente canónica en config/leagues.py
try:
    from config.leagues import LIGAS, URLS_FIXTURE, CSV_A_LIGA_ID
except ImportError:
    from config import LIGAS, URLS_FIXTURE, CSV_A_LIGA_ID



# ========== DESCARGA DE CSV - ELIMINADO CÓDIGO DUPLICADO ==========
# REFACTORIZADO: Se eliminó función descargar_csv_safe() duplicada.
# Usar exclusivamente: from utils.shared import descargar_csv_safe
# Esto centraliza la lógica y evita inconsistencias.

# ========== DICCIONARIO DE ALIAS DE EQUIPOS ==========
# REFACTORIZADO: Se eliminó ALIAS_TEAMS duplicado.
# Usar exclusivamente: from utils.shared import ALIAS_TEAMS
# La fuente canónica está en utils/shared.py


# ========== IMPORTAR MÓDULOS DE CORE Y SCRAPERS ==========
from core.prediction import (
    calcular_fuerzas,
    predecir_partido,
    predecir_partido_champions,
    predecir_partido_en_vivo,
    obtener_h2h,
)
from scrapers.fixtures_scraper import (
    obtener_proximos_partidos,
    _scrape_promiedos,
)


# ========== FUNCIÓN CACHEADA PARA DATOS HISTÓRICOS ==========
# LRU Cache standalone (no puede usarse directamente en métodos de instancia)
# Cacheamos la carga de datos por liga+temporadas para evitar múltiples lecturas

@lru_cache(maxsize=32)
def _get_cached_historical_data(liga_codigo: str, temporadas: int, url_csv: str) -> pd.DataFrame:
    """
    Función cacheada para obtener datos históricos.
    El decorator @lru_cache mantiene los DataFrames en memoria RAM.
    
    Primera llamada: Carga desde BD/CSV (lento, ~1-3s)
    Llamadas siguientes: Retorna desde caché (instantáneo, ~0.001s)
    
    Args:
        liga_codigo: Código de liga (E0, SP1, D1, etc.)
        temporadas: Número de temporadas a cargar
        url_csv: URL del CSV como identificador único
    
    Returns:
        DataFrame cacheado con datos históricos
    """
    logger.info(f"📥 Cache MISS: Cargando datos para {liga_codigo} ({temporadas} temporadas)")
    
    # Intentar cargar desde BD local primero
    if _data_provider and DB_PROVIDER_AVAILABLE:
        try:
            df = _data_provider.get_smart_data(
                liga_codigo=liga_codigo,
                url_csv=url_csv,
                temporadas=temporadas,
                enrich=True
            )
            source = df.attrs.get('source', 'BD Local')
            logger.info(f"✓ Datos cargados ({source}): {len(df)} partidos")
            return df
        except Exception as e:
            logger.warning(f"Error con BD local: {e}, usando CSV")
    
    # Fallback a CSV online
    if url_csv:
        # OPTIMIZADO: Solo cargar columnas necesarias para ahorrar RAM
        columnas_necesarias = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 
                               'HS', 'AS', 'HC', 'AC', 'HY', 'AY', 'HR', 'AR',
                               'HST', 'AST', 'HTHG', 'HTAG']
        df = descargar_csv_safe(url_csv, timeout=15, usecols=columnas_necesarias)
        logger.info(f"✓ Datos cargados desde CSV: {len(df)} partidos")
        return df
    
    raise ValueError(f"No hay fuentes de datos disponibles para {liga_codigo}")


def clear_historical_data_cache():
    """Limpia el caché de datos históricos (útil para forzar recarga)"""
    _get_cached_historical_data.cache_clear()
    logger.info("🗑️ Cache de datos históricos limpiado")


def get_cache_stats() -> dict:
    """Retorna estadísticas del caché LRU"""
    info = _get_cached_historical_data.cache_info()
    return {
        'hits': info.hits,
        'misses': info.misses,
        'maxsize': info.maxsize,
        'currsize': info.currsize,
        'hit_rate': f"{(info.hits / (info.hits + info.misses) * 100):.1f}%" if (info.hits + info.misses) > 0 else "N/A"
    }
