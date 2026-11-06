"""
History Blueprint
=================
Historial de aciertos y auditoría de predicciones vs resultados reales.
"""

from flask import Blueprint, render_template, request, flash
from timba_core import LIGAS
from services.audit_service import obtener_historial_audit

history_bp = Blueprint('history', __name__)

LIGAS_HISTORY = {
    liga['codigo']: {
        'nombre': liga['nombre'],
        'bandera': liga.get('bandera', '⚽'),
        'liga_id': liga_id
    }
    for liga_id, liga in LIGAS.items()
    if liga.get('url') is not None
}


@history_bp.route('/history', endpoint='history')
def history():
    """Muestra historial de aciertos/fallos de las predicciones."""
    default_league_code = next(iter(LIGAS_HISTORY)) if LIGAS_HISTORY else 'E0'
    league_code = request.args.get('league_code', default_league_code).upper()
    days_back = int(request.args.get('days', 7))
    
    if league_code not in LIGAS_HISTORY:
        flash(f"⚠️ Liga '{league_code}' no soportada.", "warning")
        league_code = default_league_code
        
    if days_back not in [7, 14, 30]:
        days_back = 7
        
    liga_info = LIGAS_HISTORY[league_code]
    liga_id = liga_info['liga_id']
    
    es_demo = False
    try:
        resultados, estadisticas = obtener_historial_audit(liga_id, days_back)
    except Exception:
        es_demo = True
        resultados = []
        estadisticas = {
            'total_partidos': 0,
            'evaluados': 0,
            'aciertos': 0,
            'fallos': 0,
            'sin_prediccion': 0,
            'precision': 0.0
        }
        
    return render_template(
        'results.html',
        resultados=resultados,
        estadisticas=estadisticas,
        ligas=LIGAS_HISTORY,
        liga_actual=liga_info,
        league_code=league_code,
        days_back=days_back,
        es_demo=es_demo
    )
