"""
Dashboard Blueprint
===================
Vista principal del dashboard con predicciones del día.
"""

from flask import Blueprint, render_template
from timba_core import LIGAS
from services.prediction_service import cargar_dashboard_cache, obtener_last_update

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/', endpoint='index')
def index():
    """Dashboard con partidos del día y predicciones optimizadas."""
    cache_data = cargar_dashboard_cache()
    
    if cache_data:
        stats = {
            'total_ligas': cache_data.get('total_ligas', len(LIGAS)),
            'ligas': cache_data.get('ligas', LIGAS),
            'partidos_hoy': cache_data.get('partidos_hoy', {}),
            'total_partidos_hoy': cache_data.get('total_partidos_hoy', 0),
            'last_update': obtener_last_update(),
            'updated_at': cache_data.get('updated_at', '')
        }
    else:
        stats = {
            'total_ligas': len(LIGAS),
            'ligas': LIGAS,
            'partidos_hoy': {},
            'total_partidos_hoy': 0,
            'last_update': 'Actualizando...',
            'updated_at': '',
            'cache_missing': True
        }
    
    return render_template('index.html', stats=stats)
