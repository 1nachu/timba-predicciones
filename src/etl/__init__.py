"""
ETL Package - Football Historical Data Pipeline
===============================================
Módulo modular para extracción, transformación y carga de datos históricos de fútbol.
"""

from .config import LIGAS_CONFIG, COLUMNAS_CRITICAS, COLUMNAS_TARJETAS
from .extractor import FootballDataExtractor
from .transformer import FootballDataTransformer
from .loader import FootballDataLoader, obtener_resumen_bd
from .pipeline import FootballETLPipeline

__all__ = [
    'LIGAS_CONFIG',
    'COLUMNAS_CRITICAS',
    'COLUMNAS_TARJETAS',
    'FootballDataExtractor',
    'FootballDataTransformer',
    'FootballDataLoader',
    'FootballETLPipeline',
    'obtener_resumen_bd',
]
