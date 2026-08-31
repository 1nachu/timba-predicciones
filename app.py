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
from typing import Optional
from datetime import datetime

# Inyectar 'src/' al sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from flask import Flask, render_template, request, send_from_directory, url_for
from flask_caching import Cache
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

load_dotenv()

# Inicializar Flask
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_super_secreta_timba_2026')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 2592000  # 30 días para estáticos

# Configurar FileSystemCache persistente
FLASK_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'flask_cache')
os.makedirs(FLASK_CACHE_DIR, exist_ok=True)

cache = Cache(app, config={
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
# FUNCIONES CACHEADAS (MEMOIZADAS)
# ============================================================

@cache.memoize(timeout=3600)
def cargar_datos_liga_cached(liga_id: int):
    """Carga desde BD local (con fallback a CSV) y calcula fuerzas. Memoizado: 1h."""
    liga_info = LIGAS.get(liga_id)
    if not liga_info:
        return {}, 0, 0, []
    
    codigo = liga_info.get('codigo')
    url = liga_info.get('url')
    if not codigo and not url:
        return {}, 0, 0, []
    
    try:
        from timba_core import _get_cached_historical_data
        df = _get_cached_historical_data(codigo or 'ALL', 3, url or '')
        if df is None or df.empty:
            return {}, 0, 0, []
        fuerzas, media_local, media_vis = calcular_fuerzas(df)
        equipos = sorted(list(fuerzas.keys()))
        return fuerzas, media_local, media_vis, equipos
    except Exception:
        return {}, 0, 0, []


@cache.memoize(timeout=1800)
def obtener_fixtures_cached(liga_id: int):
    """Obtiene próximos partidos cacheados por 30 minutos."""
    fixture_data = URLS_FIXTURE.get(liga_id, {})
    url_fixture = fixture_data.get('url')
    if not url_fixture:
        return []
    try:
        return obtener_proximos_partidos(url_fixture)
    except Exception:
        return []


@cache.memoize(timeout=3600)
def predecir_partido_cached(liga_id: int, local_nombre: str, visitante_nombre: str):
    """Calcula y cachea la predicción entre dos equipos por 1 hora."""
    if liga_id == 8:
        cache_todas = {
            lid: cargar_datos_liga_cached(lid)
            for lid in LIGAS
            if LIGAS[lid].get('url') is not None
        }
        return predecir_partido_champions(local_nombre, visitante_nombre, cache_todas)

    fuerzas, media_local, media_vis, equipos_validos = cargar_datos_liga_cached(liga_id)
    if not fuerzas or not equipos_validos:
        return None

    try:
        local_match = emparejar_equipo(local_nombre, equipos_validos)
        vis_match = emparejar_equipo(visitante_nombre, equipos_validos)
        if local_match in fuerzas and vis_match in fuerzas:
            return predecir_partido(local_match, vis_match, fuerzas, media_local, media_vis)
    except Exception:
        pass
    return None


def cargar_datos_liga(liga_id):
    """Wrapper de conveniencia."""
    fuerzas, media_local, media_vis, equipos = cargar_datos_liga_cached(liga_id)
    return None, fuerzas, media_local, media_vis, equipos


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
