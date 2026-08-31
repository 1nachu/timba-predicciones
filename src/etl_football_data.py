"""
ETL SCRIPT - Football Historical Data Pipeline
===============================================
Fachada y CLI para el pipeline ETL modularizado (ver src/etl/).

Mantiene compatibilidad retroactiva completa para scripts y tests existentes.

Autor: Timba Team
"""

import sys
import logging
from pathlib import Path

# Agregar directorio src al path para imports locales
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

try:
    from etl import (
        LIGAS_CONFIG,
        COLUMNAS_CRITICAS,
        COLUMNAS_TARJETAS,
        FootballDataExtractor,
        FootballDataTransformer,
        FootballDataLoader,
        FootballETLPipeline,
        obtener_resumen_bd,
    )
except ImportError:
    from src.etl import (
        LIGAS_CONFIG,
        COLUMNAS_CRITICAS,
        COLUMNAS_TARJETAS,
        FootballDataExtractor,
        FootballDataTransformer,
        FootballDataLoader,
        FootballETLPipeline,
        obtener_resumen_bd,
    )

try:
    from utils.shared import SQLITE_CONNECTION_STRING
except ImportError:
    SQLITE_CONNECTION_STRING = "sqlite:///data/databases/football_data.db"

logger = logging.getLogger(__name__)

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

# ========== PUNTO DE ENTRADA CLI ==========
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='ETL Pipeline para descarga de datos de football-data.co.uk'
    )
    parser.add_argument(
        '--db-type',
        choices=['sqlite', 'postgresql'],
        default='sqlite',
        help='Tipo de base de datos (default: sqlite)'
    )
    parser.add_argument(
        '--connection',
        type=str,
        default=SQLITE_CONNECTION_STRING,
        help=f'String de conexión a BD (default: {SQLITE_CONNECTION_STRING})'
    )
    parser.add_argument(
        '--ligas',
        type=str,
        default='E0,SP1,D1,I1,F1,P1,N1,ARG',
        help='Códigos de ligas separados por coma (default: E0,SP1,D1,I1,F1,P1,N1,ARG)'
    )
    parser.add_argument(
        '--skip-create-tables',
        action='store_true',
        help='No crear tablas'
    )
    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Solo mostrar estadísticas (no ejecutar ETL)'
    )
    parser.add_argument(
        '--historico', '--full',
        action='store_true',
        dest='historico',
        help='Descarga TODAS las temporadas (por defecto solo la actual 25/26)'
    )
    
    args = parser.parse_args()
    
    if args.stats_only:
        logger.info("Obteniendo estadísticas...")
        df_stats = obtener_resumen_bd(args.db_type, args.connection)
        print("\n" + df_stats.to_string())
    else:
        ligas_lista = args.ligas.split(',')
        solo_actual = not args.historico
        
        if solo_actual:
            logger.info("🚀 Modo RÁPIDO: Temporadas recientes (3 por liga, ej: 26/27, 25/26, 24/25)")
            logger.info("   Usa --historico para descargar todas las temporadas históricas\n")
        else:
            logger.info("📚 Modo HISTÓRICO: Descargando TODAS las temporadas (~11 por liga)")
            logger.info("   ⏱️  Esto puede tomar varios minutos...\n")
        
        pipeline = FootballETLPipeline(args.db_type, args.connection)
        exitoso = pipeline.ejecutar(
            ligas_lista, 
            crear_tablas=not args.skip_create_tables,
            solo_actual=solo_actual
        )
        
        sys.exit(0 if exitoso else 1)
