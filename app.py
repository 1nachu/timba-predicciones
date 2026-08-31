"""
Timba Predictor Web - Flask Application (Refactorizada)
========================================================

Aplicación web modularizada para predicción de resultados de fútbol.
Utiliza Flask Blueprints, FileSystemCache y servicios desacoplados.

Autor: Timba Team
Última actualización: Agosto 2026
"""

import os
import sys
from datetime import datetime

# Inyectar 'src/' al sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from flask import Flask, render_template, request, send_from_directory, url_for
from dotenv import load_dotenv

from timba_core import (
    LIGAS, URLS_FIXTURE,
    predecir_partido, predecir_partido_champions, calcular_fuerzas, obtener_proximos_partidos,
    descargar_csv_safe, emparejar_equipo,
    DB_PATH
)
from utils.shared import get_db_connection, LIVE_SCORES_DB_PATH
from utils.markets import (
    generar_recomendaciones,
    obtener_mejor_recomendacion,
    determinar_prediccion_1x2,
    calcular_semaforo,
    evaluar_value_bets,
    calcular_valor_esperado,
    calcular_criterio_kelly,
    PREDICCION_UMBRAL_GANA,
    PREDICCION_UMBRAL_DOBLE,
)
from web.cache import cache
from services import (
    determinar_resultado_real,
    determinar_prediccion_ia,
    validar_acierto,
    obtener_historial_audit,
    obtener_partidos_locales,
    limpiar_partidos_viejos,
    ordenar_partidos_por_liga,
    enriquecer_partidos_con_prediccion,
    normalizar_nombre_equipo,
    cargar_dashboard_cache,
    obtener_last_update,
)
from services.prediction_service import (
    cargar_datos_liga_cached,
    obtener_fixtures_cached,
    predecir_partido_cached,
    cargar_datos_liga,
)

load_dotenv()

# Inicializar Flask
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_super_secreta_timba_2026')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 2592000  # 30 días para estáticos

# Configurar FileSystemCache persistente
FLASK_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'flask_cache')
os.makedirs(FLASK_CACHE_DIR, exist_ok=True)

cache.init_app(app, config={
    'CACHE_TYPE': 'FileSystemCache',
    'CACHE_DIR': FLASK_CACHE_DIR,
    'CACHE_DEFAULT_TIMEOUT': 600,
    'CACHE_THRESHOLD': 500,
    'CACHE_IGNORE_ERRORS': True
})


# Context Processor para templates
@app.context_processor
def inject_globals():
    return dict(
        todas_las_ligas=LIGAS,
        current_year=datetime.now().year
    )


# ============================================================
# RESOLUCIÓN AUTOMÁTICA DE ENDPOINTS (Compatibilidad Jinja2)
# ============================================================
def _handle_url_build_error(error, endpoint, values):
    """Permite resolver url_for('fixtures') -> url_for('fixtures.fixtures') transparentemente."""
    candidates = [
        f"{endpoint}.{endpoint}",
        f"dashboard.{endpoint}",
        f"fixtures.{endpoint}",
        f"predict.{endpoint}",
        f"live.{endpoint}",
        f"history.{endpoint}",
        f"seo.{endpoint}",
    ]
    for cand in candidates:
        if cand in app.view_functions:
            return url_for(cand, **values)
    raise error

app.url_build_error_handlers.append(_handle_url_build_error)


# ============================================================
# REGISTRO DE BLUEPRINTS MODULARES
# ============================================================
from web.blueprints import (
    dashboard_bp,
    predict_bp,
    fixtures_bp,
    live_bp,
    history_bp,
    seo_bp,
    api_bp
)

app.register_blueprint(dashboard_bp)
app.register_blueprint(predict_bp)
app.register_blueprint(fixtures_bp)
app.register_blueprint(live_bp)
app.register_blueprint(history_bp)
app.register_blueprint(seo_bp)
app.register_blueprint(api_bp)


# ============================================================
# MANEJADORES DE ERROR
# ============================================================
@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', error="Página no encontrada"), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('base.html', error="Error interno del servidor"), 500


if __name__ == '__main__':
    print("=" * 50)
    print("🎯 TIMBA PREDICTOR WEB (Modular v2.2)")
    print("=" * 50)
    print(f"📊 Ligas disponibles: {len(LIGAS)}")
    print(f"📅 Fixtures configurados: {len(URLS_FIXTURE)}")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
