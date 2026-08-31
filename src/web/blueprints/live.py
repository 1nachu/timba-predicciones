"""
Live Blueprint
==============
Marcadores y partidos en vivo desde la base de datos local no bloqueante.
"""

from flask import Blueprint, render_template
from services.fixtures_service import (
    obtener_partidos_locales,
    enriquecer_partidos_con_prediccion,
    ordenar_partidos_por_liga
)

live_bp = Blueprint('live', __name__)


@live_bp.route('/live', endpoint='live')
def live():
    """Vista de partidos en vivo y del día con predicciones."""
    partidos = obtener_partidos_locales()
    if partidos:
        try:
            partidos = enriquecer_partidos_con_prediccion(partidos)
            partidos = ordenar_partidos_por_liga(partidos)
        except Exception:
            pass
    return render_template('live.html', partidos=partidos, es_demo=False)
