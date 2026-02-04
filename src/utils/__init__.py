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
)

__all__ = [
    'normalizar_csv',
    'descargar_csv_safe',
    'emparejar_equipo',
    'encontrar_equipo_similar',
    'imprimir_barra',
]
