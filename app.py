"""
Timba Predictor API - Flask Application (v3.0 API-Only)
========================================================

Backend API REST JSON para predicción de resultados de fútbol.
El frontend se sirve de manera desacoplada mediante Next.js (SSR) en el puerto 3000.

Autor: Timba Team
Última actualización: Noviembre 2026
"""

import os
import sys

# Inyectar 'src/' al sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from flask import Flask, jsonify
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
    obtener_equipos_liga,
    predecir_manual,
    warmup_caches_async,
)
from services.prediction_service import (
    cargar_datos_liga_cached,
    obtener_fixtures_cached,
    predecir_partido_cached,
    cargar_datos_liga,
)

load_dotenv()

# Inicializar Flask en modo API-only (sin static_folder ni templates Jinja)
app = Flask(__name__, static_folder=None, template_folder=None)
app.secret_key = os.getenv('SECRET_KEY', 'clave_super_secreta_timba_2026')

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

# ============================================================
# REGISTRO DEL BLUEPRINT API v1
# ============================================================
from web.blueprints import api_bp

app.register_blueprint(api_bp)

# Activar datos determinísticos si se ejecuta la suite E2E (Playwright), o precalentar cachés en background
if os.getenv('E2E_SEED_DATA') == '1':
    from tests.e2e_seed import apply_e2e_seed
    apply_e2e_seed()
else:
    warmup_caches_async()


# ============================================================
# MANEJADORES DE ERROR JSON
# ============================================================
@app.errorhandler(404)
def page_not_found(e):
    return jsonify({'error': 'Recurso o ruta no encontrada'}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Error interno del servidor'}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("🎯 TIMBA PREDICTOR API (v3.0 API-Only)")
    print("=" * 50)
    print(f"📊 Ligas disponibles: {len(LIGAS)}")
    print(f"📅 Fixtures configurados: {len(URLS_FIXTURE)}")
    print("=" * 50)
    debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug_mode, host='127.0.0.1', port=5000)
