"""
Fixtures Blueprint
==================
Calendario y próximos partidos por liga con predicciones automáticas.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from timba_core import LIGAS
from utils.markets import obtener_mejor_recomendacion
from services.prediction_service import obtener_fixtures_cached, predecir_partido_cached

fixtures_bp = Blueprint('fixtures', __name__)


@fixtures_bp.route('/fixtures', endpoint='fixtures')
def fixtures():
    """Calendario de próximos partidos con predicciones automáticas."""
    
    liga_id = int(request.args.get('liga_id', 1))
    liga_info = LIGAS.get(liga_id)
    
    if not liga_info:
        flash("❌ Liga no válida.", "danger")
        return redirect(url_for('fixtures.fixtures', liga_id=1))

    partidos = []
    partidos_raw = obtener_fixtures_cached(liga_id)
    
    if not partidos_raw:
        flash(f"📭 No se encontraron partidos próximos para {liga_info['nombre']}", "info")
    
    for p in partidos_raw:
        partido = {
            'local': p['local'],
            'visitante': p['visitante'],
            'fecha': p.get('fecha', 'Próximamente'),
            'fecha_utc': p.get('fecha_utc'),
            'prediccion': None,
            'recomendacion': None,
            'error': None
        }
        
        try:
            pred = predecir_partido_cached(liga_id, p['local'], p['visitante'])
            if pred:
                partido['prediccion'] = {
                    'local': round(pred.get('Prob_Local', 0) * 100, 1),
                    'empate': round(pred.get('Prob_Empate', 0) * 100, 1),
                    'visitante': round(pred.get('Prob_Vis', 0) * 100, 1)
                }
                partido['recomendacion'] = obtener_mejor_recomendacion(pred)
            else:
                partido['error'] = f"No encontrado: {p['local']}"
        except Exception as e:
            partido['error'] = str(e)[:30]
            
        partidos.append(partido)

    return render_template(
        'fixtures.html',
        partidos=partidos,
        liga_actual=liga_info,
        liga_id=liga_id
    )
