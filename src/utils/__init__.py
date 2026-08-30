"""
Módulo de utilidades compartidas para el proyecto Timba.
Contiene funciones comunes utilizadas por múltiples módulos.
"""

from .shared import (
    normalizar_csv,
    descargar_csv_safe,
    emparejar_equipo,
    encontrar_equipo_similar,
    imprimir_barra,
    get_db_connection,
)
from .markets import (
    PREDICCION_UMBRAL_GANA,
    PREDICCION_UMBRAL_DOBLE,
    UMBRAL_ALTO,
    UMBRAL_MEDIO,
    obtener_mejor_recomendacion,
    determinar_prediccion_1x2,
    generar_recomendaciones,
    calcular_semaforo,
    calcular_mercados_adicionales,
)

__all__ = [
    'normalizar_csv',
    'descargar_csv_safe',
    'emparejar_equipo',
    'encontrar_equipo_similar',
    'imprimir_barra',
    'get_db_connection',
    'PREDICCION_UMBRAL_GANA',
    'PREDICCION_UMBRAL_DOBLE',
    'UMBRAL_ALTO',
    'UMBRAL_MEDIO',
    'obtener_mejor_recomendacion',
    'determinar_prediccion_1x2',
    'generar_recomendaciones',
    'calcular_semaforo',
    'calcular_mercados_adicionales',
]
