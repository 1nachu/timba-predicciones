"""
Timba Predictor Web - Flask Application
========================================

Aplicación web para predicción de partidos de fútbol.
Incluye dashboard, predicciones manuales, fixtures y live scores.
OPTIMIZADO: Lee Live Scores desde DB local para evitar límites de API.

Autor: Timba Team
Última actualización: Febrero 2026
"""

# ========== IMPORTS ESTÁNDAR ==========
import os
import sys
import sqlite3
import json
from typing import Optional
from datetime import datetime, timedelta, timezone

# ============================================================
# FIX CRÍTICO DE IMPORTS
# Inyectar 'src/' al path ANTES de importar cualquier cosa de src
# ============================================================
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# ========== IMPORTS DE TERCEROS ==========
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_caching import Cache
from dotenv import load_dotenv
import pandas as pd

# ========== CONFIGURACIÓN DE CACHÉ PARA ESTÁTICOS ==========
# 30 días = 2592000 segundos (mejora puntuación PageSpeed)
SEND_FILE_MAX_AGE_DEFAULT = 2592000

# ========== IMPORTS LOCALES ==========
from timba_core import (
    LIGAS, URLS_FIXTURE,
    predecir_partido, calcular_fuerzas, obtener_proximos_partidos,
    descargar_csv_safe, emparejar_equipo
)

# Intentar importar cliente de API (opcional)
try:
    from football_api_client import FootballDataClient
    API_CLIENT_AVAILABLE = True
except ImportError:
    API_CLIENT_AVAILABLE = False
    FootballDataClient = None

# Intentar importar TeamNormalizer (opcional - mejora normalización)
try:
    from team_normalization import TeamNormalizer
    TEAM_NORMALIZER_AVAILABLE = True
except ImportError:
    TeamNormalizer = None
    TEAM_NORMALIZER_AVAILABLE = False

# Cargar configuración desde .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_super_secreta_timba_2026')

# Caché de archivos estáticos: 30 días (mejora PageSpeed)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = SEND_FILE_MAX_AGE_DEFAULT

# ============================================================
# CONFIGURACIÓN DE FLASK-CACHING (OPTIMIZADO PARA RASPBERRY PI)
# ============================================================
# SimpleCache: Almacena en memoria RAM del proceso
# Ideal para Raspberry Pi y aplicaciones single-process
cache = Cache(app, config={
    'CACHE_TYPE': 'SimpleCache',           # Caché en memoria RAM
    'CACHE_DEFAULT_TIMEOUT': 600,           # Timeout por defecto: 10 minutos
    'CACHE_THRESHOLD': 200                  # Máximo 200 items en caché
})


# ============================================================
# FUNCIONES CACHEADAS CON MEMOIZE (DATOS PESADOS)
# ============================================================
@cache.memoize(timeout=3600)  # 1 hora - Los datos históricos cambian poco
def cargar_datos_liga_cached(liga_id: int):
    """
    Versión CACHEADA de cargar_datos_liga.
    Descarga CSV y calcula fuerzas. MEMOIZADO: 1 hora.
    
    Args:
        liga_id: ID de la liga en LIGAS
    
    Returns:
        tuple: (fuerzas, media_local, media_vis, equipos) o valores vacíos si falla
    """
    liga_info = LIGAS.get(liga_id)
    if not liga_info:
        return {}, 0, 0, []
    
    try:
        # Descargar CSV de la liga (operación lenta)
        # OPTIMIZADO: Solo cargar columnas esenciales para ahorrar memoria RAM
        columnas_necesarias = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 
                               'HS', 'AS', 'HC', 'AC', 'HY', 'AY', 'HR', 'AR',
                               'HST', 'AST', 'HTHG', 'HTAG']
        df = descargar_csv_safe(liga_info['url'], usecols=columnas_necesarias)
        
        if df is None or df.empty:
            return {}, 0, 0, []
        
        # Calcular fuerzas (operación CPU-intensiva)
        fuerzas, media_local, media_vis = calcular_fuerzas(df)
        equipos = sorted(list(fuerzas.keys()))
        
        print(f"✅ Liga {liga_id} cacheada: {len(equipos)} equipos")
        return fuerzas, media_local, media_vis, equipos
        
    except Exception as e:
        print(f"❌ Error cargando liga {liga_id}: {e}")
        return {}, 0, 0, []


@cache.memoize(timeout=1800)  # 30 minutos - Los fixtures cambian moderadamente
def obtener_fixtures_cached(liga_id: int):
    """
    Versión CACHEADA de obtener próximos partidos.
    Hace scraping de fixtures. MEMOIZADO: 30 minutos.
    
    Args:
        liga_id: ID de la liga en URLS_FIXTURE
    
    Returns:
        list: Lista de partidos raw o lista vacía si falla
    """
    fixture_data = URLS_FIXTURE.get(liga_id, {})
    url_fixture = fixture_data.get('url')
    
    if not url_fixture:
        return []
    
    try:
        partidos = obtener_proximos_partidos(url_fixture)
        print(f"✅ Fixtures liga {liga_id} cacheados: {len(partidos)} partidos")
        return partidos
    except Exception as e:
        print(f"❌ Error obteniendo fixtures {liga_id}: {e}")
        return []


@cache.memoize(timeout=3600)  # 1 hora - Predicciones individuales cacheadas
def predecir_partido_cached(liga_id: int, local_nombre: str, visitante_nombre: str):
    """
    Realiza la predicción y guarda el resultado en memoria RAM por 1 hora.
    Evita recalcular matemáticas pesadas (Poisson) si el partido ya fue consultado.
    
    OPTIMIZACIÓN CPU: Esta función cachea el resultado de predecir_partido()
    individualmente por cada combinación liga+local+visitante.
    
    Args:
        liga_id: ID de la liga en LIGAS
        local_nombre: Nombre del equipo local (sin normalizar)
        visitante_nombre: Nombre del equipo visitante (sin normalizar)
    
    Returns:
        dict: Predicción con probabilidades o None si falla
    """
    # Recuperamos fuerzas (ya cacheado por 1 hora)
    fuerzas, media_local, media_vis, equipos_validos = cargar_datos_liga_cached(liga_id)
    
    if not fuerzas or not equipos_validos:
        return None

    try:
        # Normalizamos nombres dentro de la función cacheada
        local_match = emparejar_equipo(local_nombre, equipos_validos)
        vis_match = emparejar_equipo(visitante_nombre, equipos_validos)
        
        if local_match in fuerzas and vis_match in fuerzas:
            # Cálculo matemático pesado (Poisson) - se cachea por 1 hora
            return predecir_partido(local_match, vis_match, fuerzas, media_local, media_vis)
            
    except Exception as e:
        print(f"❌ Error en predicción cacheada {local_nombre} vs {visitante_nombre}: {e}")
        
    return None


# ============================================================
# HELPER: Cache condicional solo para GET requests
# ============================================================
def cache_get_only(timeout=300, key_prefix='view'):
    """
    Decorador que cachea solo requests GET.
    POST requests pasan sin caché para resultados dinámicos.
    """
    def decorator(f):
        # Crear versión cacheada de la función
        cached_f = cache.cached(timeout=timeout, query_string=True, key_prefix=key_prefix)(f)
        
        def wrapper(*args, **kwargs):
            if request.method == 'GET':
                return cached_f(*args, **kwargs)
            else:
                return f(*args, **kwargs)
        
        wrapper.__name__ = f.__name__
        wrapper.__doc__ = f.__doc__
        return wrapper
    return decorator


# ============================================================
# HELPER: Cargar datos de una liga (WRAPPER que usa caché)
# ============================================================
def cargar_datos_liga(liga_id):
    """
    Carga datos históricos de una liga usando la versión cacheada.
    Retorna: (df, fuerzas, media_local, media_vis, equipos) o valores vacíos si falla.
    
    NOTA: df se retorna como None porque ya no lo necesitamos después de calcular fuerzas.
    """
    fuerzas, media_local, media_vis, equipos = cargar_datos_liga_cached(liga_id)
    return None, fuerzas, media_local, media_vis, equipos


# ============================================================
# HELPER: Generar recomendaciones (Semáforo)
# ============================================================
def generar_recomendaciones(prediccion, umbral_alto=0.70, umbral_medio=0.55):
    """
    Genera lista de recomendaciones basada en probabilidades.
    Incluye: Goles, Córners y Tarjetas.
    """
    recos = []
    
    # ========== REGLAS DE GOLES ==========
    reglas_goles = [
        ('Prob_1X', 'Doble Oportunidad: Local o Empate', '1X', '⚽'),
        ('Prob_X2', 'Doble Oportunidad: Empate o Visitante', 'X2', '⚽'),
        ('Prob_12', 'Sin Empate: Gana alguien', '12', '⚽'),
        ('Over_15', 'Más de 1.5 Goles', 'Over 1.5 Goles', '⚽'),
        ('Over_25', 'Más de 2.5 Goles', 'Over 2.5 Goles', '⚽'),
        ('Under_35', 'Menos de 3.5 Goles (Seguridad)', 'Under 3.5 Goles', '⚽'),
    ]
    
    # ========== REGLAS DE CÓRNERS ==========
    reglas_corners = [
        ('Over_85', 'Más de 8.5 Córners', 'Over 8.5 Córners', '🚩'),
        ('Over_95', 'Más de 9.5 Córners', 'Over 9.5 Córners', '🚩'),
        ('Prob_Local_Mas_Corners', 'Local saca más córners', 'Local +Córners', '🚩'),
    ]
    
    # ========== REGLAS DE TARJETAS ==========
    reglas_tarjetas = [
        ('Over_25_Cards', 'Más de 2.5 Tarjetas Amarillas', 'Over 2.5 Tarjetas', '🟨'),
        ('Over_35_Cards', 'Más de 3.5 Tarjetas Amarillas', 'Over 3.5 Tarjetas', '🟨'),
        ('Over_45_Cards', 'Más de 4.5 Tarjetas Amarillas', 'Over 4.5 Tarjetas', '🟨'),
        ('Under_55_Cards', 'Menos de 5.5 Tarjetas (Seguro)', 'Under 5.5 Tarjetas', '🟨'),
    ]
    
    # Procesar todas las reglas
    todas_reglas = reglas_goles + reglas_corners + reglas_tarjetas
    
    for key, texto, corto, emoji in todas_reglas:
        prob = prediccion.get(key, 0)
        if prob >= umbral_alto:
            recos.append({
                'tipo': 'fuego',
                'texto': texto,
                'corto': corto,
                'prob': round(prob * 100, 1),
                'icon': '🔥',
                'emoji': emoji,
                'class': 'success'
            })
        elif prob >= umbral_medio:
            recos.append({
                'tipo': 'alerta',
                'texto': texto,
                'corto': corto,
                'prob': round(prob * 100, 1),
                'icon': '⚠️',
                'emoji': emoji,
                'class': 'warning'
            })
    
    # ========== REGLA ESPECIAL: Tarjeta Roja ==========
    # Umbral más bajo porque las rojas son raras (>15% ya es notable)
    prob_roja = prediccion.get('Prob_Red_Card', 0)
    if prob_roja >= 0.20:
        recos.append({
            'tipo': 'fuego',
            'texto': 'Alta probabilidad de Tarjeta Roja',
            'corto': 'Habrá Roja',
            'prob': round(prob_roja * 100, 1),
            'icon': '🔥',
            'emoji': '🟥',
            'class': 'danger'
        })
    elif prob_roja >= 0.12:
        recos.append({
            'tipo': 'alerta',
            'texto': 'Posible Tarjeta Roja en el partido',
            'corto': 'Roja Posible',
            'prob': round(prob_roja * 100, 1),
            'icon': '⚠️',
            'emoji': '🟥',
            'class': 'warning'
        })
    
    # Ordenar por probabilidad descendente
    recos.sort(key=lambda x: x['prob'], reverse=True)
    
    return recos


def obtener_mejor_recomendacion(prediccion):
    """Retorna la mejor apuesta corta para la tabla de fixtures."""
    prob_local = prediccion.get('Prob_Local', 0)
    prob_empate = prediccion.get('Prob_Empate', 0)
    prob_vis = prediccion.get('Prob_Vis', 0)
    
    # Buscar la mayor probabilidad base
    if prob_local >= 0.55:
        return f"1 ({round(prob_local*100)}%)"
    elif prob_vis >= 0.55:
        return f"2 ({round(prob_vis*100)}%)"
    elif prediccion.get('Prob_1X', 0) >= 0.70:
        return "1X"
    elif prediccion.get('Prob_X2', 0) >= 0.70:
        return "X2"
    elif prediccion.get('Over_25', 0) >= 0.65:
        return "Over 2.5"
    elif prediccion.get('Over_15', 0) >= 0.75:
        return "Over 1.5"
    else:
        return "—"


# ============================================================
# HELPER: Limpiar partidos viejos de la DB (>24 horas)
# ============================================================
def limpiar_partidos_viejos():
    """
    Elimina partidos con más de 24 horas de antigüedad.
    Ejecutar antes de cada consulta para mantener DB limpia.
    """
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'databases', 'live_scores.db')
    
    if not os.path.exists(db_path):
        return 0
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Timestamp de hace 24 horas
        limite_24h = (datetime.now() - timedelta(hours=24)).timestamp()
        
        # Eliminar snapshots viejos
        cursor.execute("""
            DELETE FROM match_snapshots 
            WHERE timestamp < ?
        """, (limite_24h,))
        
        deleted = cursor.rowcount
        
        # También limpiar eventos viejos
        cursor.execute("""
            DELETE FROM match_events 
            WHERE timestamp < ?
        """, (limite_24h,))
        
        conn.commit()
        conn.close()
        
        if deleted > 0:
            print(f"🧹 Limpieza: {deleted} partidos antiguos eliminados")
        
        return deleted
    except Exception as e:
        print(f"⚠️ Error limpiando DB: {e}")
        return 0


# ============================================================
# HELPER: Leer Partidos desde DB Local (OPTIMIZADO)
# ============================================================
def obtener_partidos_locales():
    """
    Lee los partidos en vivo desde la base de datos local (live_scores.db).
    
    OPTIMIZADO:
    - Filtra solo partidos del día actual
    - Limita a 50 partidos máximo
    - Ejecuta limpieza automática de partidos >24h
    """
    # Ruta absoluta a la base de datos para evitar errores
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'databases', 'live_scores.db')
    partidos = []
    
    if not os.path.exists(db_path):
        print(f"⚠️ Base de datos no encontrada: {db_path}")
        return []
    
    # Limpieza automática de partidos viejos (>24h)
    limpiar_partidos_viejos()
    
    try:
        # Conectar en modo solo lectura (URI mode) para no bloquear escrituras del servicio
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        cursor = conn.cursor()
        
        # Calcular timestamp del inicio del día actual (00:00:00)
        ahora = datetime.now()
        inicio_dia = datetime(ahora.year, ahora.month, ahora.day, 0, 0, 0).timestamp()            
        fin_dia = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59).timestamp()

        # Query 1: partidos en vivo ahora
        cursor.execute("""
            SELECT data, 'live' as seccion FROM match_snapshots 
            WHERE status IN ('LIVE', 'IN_PLAY', 'PAUSED', 'HALFTIME')
            ORDER BY timestamp ASC
            LIMIT 20
        """)
        rows_live = cursor.fetchall()

        # Query 2: partidos programados para hoy
        cursor.execute("""
            SELECT data, 'proximos' as seccion FROM match_snapshots 
            WHERE status IN ('TIMED', 'SCHEDULED')
            AND timestamp >= ?
            AND timestamp <= ?
            ORDER BY timestamp ASC
            LIMIT 30
        """, (inicio_dia,))
        rows_proximos = cursor.fetchall()

        rows = rows_live + rows_proximos
        
        for row in rows:
            try:
                snap = json.loads(row[0])
                seccion = row[1]
                
                # Traducir formato DB -> Formato Web (compatible con tu template)
                partido = {
                    'home': snap['home_team'],
                    'away': snap['away_team'],
                    'score': f"{snap['home_score']}-{snap['away_score']}",
                    'status': 'EN VIVO' if snap['status'] == 'LIVE' else snap['status'],
                    'minute': snap.get('minute', ''),
                    'competition': {
                        'code': snap.get('competition', ''),
                        'name': snap.get('competition', '')
                    },
                    # Datos extra necesarios para la lógica de predicción
                    'homeTeam': {'name': snap['home_team']},
                    'awayTeam': {'name': snap['away_team']},
                    'utcDate': snap.get('utcDate', datetime.fromtimestamp(snap.get('timestamp', ahora.timestamp())).isoformat()),
                    '_timestamp': snap.get('timestamp', 0), # Para filtrado JS
                    'seccion': seccion
                }
                partidos.append(partido)
            except Exception as e:
                print(f"Error procesando fila de DB: {e}")
                continue
                
        conn.close()
        print(f"✅ Live: {len(rows_live)} en vivo, {len(rows_proximos)} próximos")
    except Exception as e:
        print(f"⚠️ Error leyendo DB local: {e}")
        
    return partidos


# ============================================================
# CONTEXT PROCESSOR: Variables globales en templates
# ============================================================
@app.context_processor
def inject_globals():
    return dict(
        todas_las_ligas=LIGAS,
        current_year=datetime.now().year
    )


# ============================================================
# RUTA: Dashboard Principal (OPTIMIZADO - Lee desde JSON)
# ============================================================
# Ruta al archivo de caché generado por background_updater.py
DASHBOARD_CACHE_FILE = os.path.join(os.path.dirname(__file__), 'data', 'dashboard_cache.json')


def cargar_dashboard_cache() -> dict:
    """
    Carga datos pre-calculados desde data/dashboard_cache.json.
    Generado por background_updater.py en segundo plano.
    
    Returns:
        dict: Datos del cache o estructura vacía si falla
    """
    try:
        if os.path.exists(DASHBOARD_CACHE_FILE):
            with open(DASHBOARD_CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convertir keys de partidos_hoy de string a int
            if 'partidos_hoy' in data:
                data['partidos_hoy'] = {
                    int(k): v for k, v in data['partidos_hoy'].items()
                }
            
            # Convertir keys de ligas de string a int
            if 'ligas' in data:
                data['ligas'] = {
                    int(k): v for k, v in data['ligas'].items()
                }
            
            return data
    except Exception as e:
        print(f"⚠️ Error cargando dashboard cache: {e}")
    
    return None


def obtener_last_update() -> str:
    """
    Calcula tiempo desde última actualización del cache.
    
    Returns:
        str: Texto legible (ej: "hace 5 minutos")
    """
    try:
        if os.path.exists(DASHBOARD_CACHE_FILE):
            mtime = os.path.getmtime(DASHBOARD_CACHE_FILE)
            dt_modificacion = datetime.fromtimestamp(mtime)
            ahora = datetime.now()
            
            delta = ahora - dt_modificacion
            minutos = int(delta.total_seconds() / 60)
            
            if minutos < 1:
                return "hace menos de 1 minuto"
            elif minutos == 1:
                return "hace 1 minuto"
            elif minutos < 60:
                return f"hace {minutos} minutos"
            else:
                horas = minutos // 60
                if horas == 1:
                    return "hace 1 hora"
                else:
                    return f"hace {horas} horas"
    except:
        pass
    
    return "desconocido"


@app.route('/')
def index():
    """
    Dashboard con partidos del día y predicciones.
    
    OPTIMIZADO: Lee datos pre-calculados desde JSON.
    El scraping y cálculos se ejecutan en background_updater.py.
    Tiempo de respuesta: ~10ms (antes: 5-10 segundos).
    """
    # Cargar datos desde cache JSON (instantáneo)
    cache_data = cargar_dashboard_cache()
    
    if cache_data:
        # Datos cargados exitosamente desde cache
        stats = {
            'total_ligas': cache_data.get('total_ligas', len(LIGAS)),
            'ligas': cache_data.get('ligas', LIGAS),
            'partidos_hoy': cache_data.get('partidos_hoy', {}),
            'total_partidos_hoy': cache_data.get('total_partidos_hoy', 0),
            'last_update': obtener_last_update(),
            'updated_at': cache_data.get('updated_at', '')
        }
    else:
        # Cache no disponible - mostrar estado vacío
        stats = {
            'total_ligas': len(LIGAS),
            'ligas': LIGAS,
            'partidos_hoy': {},
            'total_partidos_hoy': 0,
            'last_update': 'Actualizando...',
            'updated_at': '',
            'cache_missing': True  # Flag para mostrar mensaje en template
        }
        print("⚠️ Dashboard cache no encontrado. Ejecuta: python background_updater.py")
    
    return render_template('index.html', stats=stats)


# ============================================================
# RUTA: Predicción Manual (Híbrida: GET y POST)
# ============================================================
@app.route('/predict', methods=['GET', 'POST'])
@cache_get_only(timeout=300, key_prefix='predict_form')
def predict():
    """
    Formulario de predicción manual entre dos equipos.
    CACHEADO: Solo GET (60s). POST siempre dinámico.
    
    Soporta dos modos:
    - GET con parámetros ?local=X&visitante=Y&liga_id=Z (desde fixtures)
    - POST desde formulario manual
    
    Normaliza automáticamente los nombres de equipos.
    """
    
    # Liga seleccionada (default: Premier League)
    liga_id = int(request.args.get('liga_id', request.form.get('liga_id', 1)))
    
    # Cargar datos de la liga
    df, fuerzas, media_local, media_vis, equipos = cargar_datos_liga(liga_id)
    
    if not equipos:
        flash(f"⚠️ No se pudieron cargar datos de la liga. Verifica tu conexión.", "warning")
    
    prediction = None
    recomendaciones = []
    seleccion_local = None
    seleccion_visita = None
    h2h = []
    
    # Obtener equipos de GET o POST
    if request.method == 'POST':
        seleccion_local = request.form.get('local')
        seleccion_visita = request.form.get('visitante')
    else:
        # GET: Puede venir desde /fixtures con ?local=X&visitante=Y
        seleccion_local = request.args.get('local')
        seleccion_visita = request.args.get('visitante')
    
    # Si tenemos equipos seleccionados, ejecutar predicción
    if seleccion_local and seleccion_visita and seleccion_local != seleccion_visita:
        
        # NORMALIZACIÓN CRÍTICA: Los nombres de fixtures pueden no coincidir
        # con la base de datos histórica. Usamos emparejar_equipo para corregirlos.
        equipos_validos = list(fuerzas.keys()) if fuerzas else []
        
        if equipos_validos:
            # Normalizar nombres usando fuzzy matching
            local_normalizado = emparejar_equipo(seleccion_local, equipos_validos)
            visitante_normalizado = emparejar_equipo(seleccion_visita, equipos_validos)
            
            # Verificar si la normalización encontró coincidencias válidas
            if local_normalizado in fuerzas and visitante_normalizado in fuerzas:
                # Calcular predicción con nombres normalizados
                prediction = predecir_partido(
                    local_normalizado, 
                    visitante_normalizado, 
                    fuerzas, 
                    media_local, 
                    media_vis
                )
                
                if prediction:
                    recomendaciones = generar_recomendaciones(prediction)
                    
                    # Actualizar nombres para mostrar los normalizados
                    # (mantener originales en display pero usar normalizados internamente)
                    if local_normalizado != seleccion_local:
                        flash(f"ℹ️ '{seleccion_local}' normalizado a '{local_normalizado}'", "info")
                    if visitante_normalizado != seleccion_visita:
                        flash(f"ℹ️ '{seleccion_visita}' normalizado a '{visitante_normalizado}'", "info")
                    
                    # Usar nombres normalizados para la visualización
                    seleccion_local = local_normalizado
                    seleccion_visita = visitante_normalizado
            else:
                # No se encontró coincidencia
                errores = []
                if local_normalizado not in fuerzas:
                    errores.append(f"'{seleccion_local}' → no encontrado (intenté: '{local_normalizado}')")
                if visitante_normalizado not in fuerzas:
                    errores.append(f"'{seleccion_visita}' → no encontrado (intenté: '{visitante_normalizado}')")
                flash(f"❌ Equipos no encontrados en BD: {', '.join(errores)}", "danger")
        else:
            flash("❌ No hay datos de equipos disponibles para esta liga.", "danger")
    
    elif seleccion_local and seleccion_visita and seleccion_local == seleccion_visita:
        flash("⚠️ Debes seleccionar dos equipos diferentes.", "warning")

    return render_template('predict.html', 
                           equipos=equipos, 
                           prediction=prediction, 
                           recomendaciones=recomendaciones,
                           seleccion_local=seleccion_local,
                           seleccion_visita=seleccion_visita,
                           liga_id=liga_id,
                           liga_actual=LIGAS.get(liga_id, {}))


# ============================================================
# RUTA: Próximos Partidos (Fixtures)
# ============================================================
@app.route('/fixtures')
@cache.cached(timeout=300, query_string=True, key_prefix='fixtures_calendar')
def fixtures():
    """Calendario de próximos partidos con predicciones automáticas. CACHEADO: 5 min."""
    
    # Obtener ID de liga del parámetro GET
    liga_id = int(request.args.get('liga_id', 1))
    liga_info = LIGAS.get(liga_id)
    
    if not liga_info:
        flash("❌ Liga no válida.", "danger")
        return redirect(url_for('fixtures', liga_id=1))

    partidos = []
    
    # Usar funciones cacheadas para máximo rendimiento
    partidos_raw = obtener_fixtures_cached(liga_id)
    
    if not partidos_raw:
        flash(f"📭 No se encontraron partidos próximos para {liga_info['nombre']}", "info")
    
    for p in partidos_raw:
        partido = {
            'local': p['local'],
            'visitante': p['visitante'],
            'fecha': p.get('fecha', 'Próximamente'),
            'fecha_utc': p.get('fecha_utc'),  # ISO 8601 para conversión JS a hora local
            'prediccion': None,
            'recomendacion': None,
            'error': None
        }
        
        # Usar función MEMOIZADA para predicción (cacheada 1 hora por partido)
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

    return render_template('fixtures.html', 
                           partidos=partidos, 
                           liga_actual=liga_info,
                           liga_id=liga_id)


# ============================================================
# RUTA: Partidos en Vivo
# ============================================================

# Orden de prioridad para ligas en Live Scores (0 = máxima prioridad)
LIGA_PRIORIDAD = {
    'ASL': 0,   # Argentina Superliga (Liga Profesional) - MÁXIMA PRIORIDAD
    'PSA': 0,   # Argentina (código alternativo API)
    'LPF': 0,   # Liga Profesional de Fútbol (código alternativo)
    'PL': 1,    # Premier League
    'BL1': 2,   # Bundesliga
    'PD': 3,    # La Liga (Primera División)
    'SA': 4,    # Serie A
    'FL1': 5,   # Ligue 1
    'PPL': 6,   # Primeira Liga (Portugal)
    'DED': 7,   # Eredivisie (Países Bajos)
    'CL': 8,    # Champions League
    'EL': 9,    # Europa League
}

# Mapeo de códigos de liga: API Football-Data.org → liga_id interno
# Esto permite buscar en la constante LIGAS para obtener URLs
API_TO_LIGA_ID = {
    'ASL': 10,   # Argentina Superliga → LIGAS[10] (ARG)
    'PSA': 10,   # Argentina (código alternativo) → LIGAS[10]
    'LPF': 10,   # Liga Profesional de Fútbol → LIGAS[10]
    'PL': 1,     # Premier League → LIGAS[1] (E0)
    'BL1': 4,    # Bundesliga → LIGAS[4] (D1)
    'PD': 2,     # La Liga → LIGAS[2] (SP1)
    'SA': 3,     # Serie A → LIGAS[3] (I1)
    'FL1': 5,    # Ligue 1 → LIGAS[5] (F1)
    'PPL': 6,    # Primeira Liga → LIGAS[6] (P1)
    'DED': 7,    # Eredivisie → LIGAS[7] (N1)
    'CL': 8,     # Champions League → LIGAS[8]
    'EL': 9,     # Europa League → LIGAS[9]
}

# Mapeo de códigos de API a códigos de liga (para filtrado de normalización)
API_TO_LEAGUE_CODE = {
    'ASL': 'ARG',  # Argentina Superliga
    'PSA': 'ARG',  # Argentina (código alternativo)
    'LPF': 'ARG',  # Liga Profesional de Fútbol
    'PL': 'E0',    # Premier League
    'BL1': 'D1',   # Bundesliga
    'PD': 'SP1',   # La Liga
    'SA': 'I1',    # Serie A
    'FL1': 'F1',   # Ligue 1
    'PPL': 'P1',   # Primeira Liga (Portugal)
    'DED': 'N1',   # Eredivisie (Países Bajos)
}

# Caché de datos históricos para evitar recargas repetidas durante la sesión
_cache_fuerzas = {}

# Instancia global del normalizador (lazy initialization)
_team_normalizer = None


def _get_team_normalizer():
    """
    Obtiene instancia singleton de TeamNormalizer.
    Usa lazy initialization para evitar errores si la BD no existe.
    """
    global _team_normalizer
    if _team_normalizer is None and TEAM_NORMALIZER_AVAILABLE and TeamNormalizer is not None:
        try:
            # Usar ruta centralizada (TeamNormalizer usa su propia ruta por defecto)
            _team_normalizer = TeamNormalizer()
            print("✅ TeamNormalizer inicializado correctamente")
        except Exception as e:
            print(f"⚠️ No se pudo inicializar TeamNormalizer: {e}")
    return _team_normalizer


def _normalizar_nombre_equipo(nombre_api: str, equipos_validos: list, league_id: Optional[str] = None) -> tuple:
    """
    Normaliza un nombre de equipo usando múltiples estrategias.
    Versión simplificada para Live Scores desde DB local.
    
    Args:
        nombre_api: Nombre del equipo desde la API
        equipos_validos: Lista de nombres válidos en datos históricos
        league_id: Código de liga para filtrar (E0, SP1, D1, I1, F1)
    
    Returns:
        tuple: (nombre_normalizado, metodo_usado, confianza)
    """
    normalizer = _get_team_normalizer()
    
    # ESTRATEGIA 1: TeamNormalizer (BD de aliases)
    if normalizer is not None:
        try:
            uuid, confianza = normalizer.normalize_team(
                team_name=nombre_api,
                league_id=league_id,
                create_if_missing=False
            )
            
            if uuid and confianza >= 60.0:
                team_info = normalizer.get_team(uuid)
                if team_info and team_info['official_name'] in equipos_validos:
                    return (team_info['official_name'], 'normalizer', confianza)
        except:
            pass
    
    # ESTRATEGIA 2: Fuzzy matching directo (fallback)
    match = emparejar_equipo(nombre_api, equipos_validos)
    if match in equipos_validos:
        return (match, 'fuzzy', 80.0)
    
    return (nombre_api, 'none', 0.0)


def _construir_codigo_to_url() -> dict:
    """
    Construye un diccionario auxiliar que mapea código CSV → URL.
    Ejemplo: {'E0': 'https://...', 'D1': 'https://...', ...}
    
    Esto permite buscar rápidamente la URL de descarga para cualquier liga.
    """
    codigo_to_url = {}
    for liga_id, liga_info in LIGAS.items():
        if isinstance(liga_info, dict):
            codigo = liga_info.get('codigo', '')
            url = liga_info.get('url', '')
            if codigo and url:
                codigo_to_url[codigo] = url
    return codigo_to_url


def ordenar_partidos_por_liga(partidos: list) -> list:
    """
    Ordena partidos por prioridad de liga.
    Premier League primero, luego Bundesliga, La Liga, etc.
    Partidos de ligas desconocidas van al final.
    """
    def get_prioridad(partido):
        try:
            if isinstance(partido, dict):
                competition = partido.get('competition', {})
                if isinstance(competition, dict):
                    codigo = competition.get('code', '')
                    return LIGA_PRIORIDAD.get(codigo, 999)
            return 999
        except (KeyError, TypeError):
            return 999
    
    return sorted(partidos, key=get_prioridad)


def enriquecer_partidos_con_prediccion(partidos: list) -> list:
    """
    Enriquece cada partido con predicción basada en datos históricos.
    Versión simplificada para Live Scores desde DB local.
    """
    global _cache_fuerzas
    
    for partido in partidos:
        partido['prediccion_timba'] = None
        try:
            competition = partido.get('competition', {})
            api_code = competition.get('code', '') if isinstance(competition, dict) else ''
            
            if api_code not in API_TO_LIGA_ID:
                continue
            
            liga_id = API_TO_LIGA_ID[api_code]
            
            # Cargar datos históricos (con caché)
            if liga_id not in _cache_fuerzas:
                liga_info = LIGAS.get(liga_id)
                if liga_info:
                    # OPTIMIZADO: Solo cargar columnas necesarias
                    columnas_necesarias = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 
                                           'HS', 'AS', 'HC', 'AC', 'HY', 'AY', 'HR', 'AR',
                                           'HST', 'AST', 'HTHG', 'HTAG']
                    df = descargar_csv_safe(liga_info.get('url'), usecols=columnas_necesarias)
                    if df is not None and not df.empty:
                        fuerzas, ml, mv = calcular_fuerzas(df)
                        _cache_fuerzas[liga_id] = {
                            'fuerzas': fuerzas, 
                            'ml': ml, 
                            'mv': mv, 
                            'equipos': sorted(list(fuerzas.keys()))
                        }
            
            cache = _cache_fuerzas.get(liga_id)
            if not cache:
                continue
            
            home_name = partido['homeTeam']['name']
            away_name = partido['awayTeam']['name']
            league_code = API_TO_LEAGUE_CODE.get(api_code)
            
            local_norm, _, _ = _normalizar_nombre_equipo(home_name, cache['equipos'], league_id=league_code)
            vis_norm, _, _ = _normalizar_nombre_equipo(away_name, cache['equipos'], league_id=league_code)
            
            if local_norm in cache['fuerzas'] and vis_norm in cache['fuerzas']:
                pred = predecir_partido(local_norm, vis_norm, cache['fuerzas'], cache['ml'], cache['mv'])
                if pred:
                    partido['prediccion_timba'] = {
                        'prob_local': round(pred.get('Prob_Local', 0) * 100, 1),
                        'prob_empate': round(pred.get('Prob_Empate', 0) * 100, 1),
                        'prob_visitante': round(pred.get('Prob_Vis', 0) * 100, 1),
                        'local_normalizado': local_norm,
                        'visitante_normalizado': vis_norm
                    }
        except Exception as e:
            print(f"Err enrich: {e}")
    
    return partidos


@app.route('/live')
@cache.cached(timeout=15, key_prefix='live_matches_local')
def live():
    """
    Ruta Live Optimizada: Lee de DB Local en lugar de API externa.
    
    VENTAJAS:
    - Sin límites de API (la DB se actualiza por servicio separado)
    - Respuesta instantánea (~10ms vs ~2s de API)
    - Cacheado 15 segundos para balance entre frescura y rendimiento
    """
    es_demo = False
    
    # 1. Leer de la base de datos local (¡Súper Rápido!)
    partidos = obtener_partidos_locales()
    
    # 2. Enriquecer con predicciones
    if partidos:
        try:
            partidos = enriquecer_partidos_con_prediccion(partidos)
            partidos = ordenar_partidos_por_liga(partidos)
        except Exception as e:
            print(f"❌ Error enriqueciendo: {e}")
    else:
        # Si no hay datos, no mostramos nada (el servicio aún no ha poblado la DB)
        pass

    return render_template('live.html', partidos=partidos, es_demo=es_demo)


# ============================================================
# RUTA: Historial de Aciertos (Accuracy History)
# ============================================================

# Ligas disponibles para el historial (con API Football-Data.org)
LIGAS_HISTORY = {
    'PL': {'nombre': 'Premier League', 'bandera': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'liga_id': 1},
    'PD': {'nombre': 'La Liga', 'bandera': '🇪🇸', 'liga_id': 2},
    'SA': {'nombre': 'Serie A', 'bandera': '🇮🇹', 'liga_id': 3},
    'BL1': {'nombre': 'Bundesliga', 'bandera': '🇩🇪', 'liga_id': 4},
    'FL1': {'nombre': 'Ligue 1', 'bandera': '🇫🇷', 'liga_id': 5},
    'PPL': {'nombre': 'Primeira Liga', 'bandera': '🇵🇹', 'liga_id': 6},
    'DED': {'nombre': 'Eredivisie', 'bandera': '🇳🇱', 'liga_id': 7},
    # Nota: Argentina (ASL) no disponible - API gratuita no la soporta
}


def determinar_resultado_real(home_goals: int, away_goals: int) -> str:
    """
    Determina el resultado real basado en los goles.
    
    Returns:
        'HOME_WIN', 'DRAW' o 'AWAY_WIN'
    """
    if home_goals > away_goals:
        return 'HOME_WIN'
    elif home_goals < away_goals:
        return 'AWAY_WIN'
    else:
        return 'DRAW'


def determinar_prediccion_ia(prediccion: dict) -> tuple:
    """
    Determina qué predijo la IA con lógica de Doble Oportunidad.
    
    Lógica:
    1. Si prob_local > 50% → "HOME_WIN"
    2. Si prob_visitante > 50% → "AWAY_WIN"
    3. Si ninguno supera 50%, evalúa doble oportunidad:
       - 1X = prob_local + prob_empate
       - X2 = prob_visitante + prob_empate
       - 12 = prob_local + prob_visitante
       - Elige la mayor combinación
    
    Returns:
        tuple: (prediccion_codigo, texto_display, probabilidad_display)
               Ej: ('HOME_WIN', 'Local', 55.3) o ('1X', '1X', 78.5)
    """
    prob_local = prediccion.get('Prob_Local', 0)
    prob_empate = prediccion.get('Prob_Empate', 0)
    prob_vis = prediccion.get('Prob_Vis', 0)
    
    # Convertir a porcentaje para comparación
    pl_pct = prob_local * 100
    pe_pct = prob_empate * 100
    pv_pct = prob_vis * 100
    
    # Caso 1: Local supera 50%
    if pl_pct > 50:
        return ('HOME_WIN', 'Local', round(pl_pct, 1))
    
    # Caso 2: Visitante supera 50%
    if pv_pct > 50:
        return ('AWAY_WIN', 'Visitante', round(pv_pct, 1))
    
    # Caso 3: Ninguno supera 50% → Doble Oportunidad
    p_1X = pl_pct + pe_pct  # Local o Empate
    p_X2 = pv_pct + pe_pct  # Visitante o Empate
    p_12 = pl_pct + pv_pct  # Local o Visitante (sin empate)
    
    # Encontrar la mayor combinación
    max_combo = max(p_1X, p_X2, p_12)
    
    if max_combo == p_1X:
        return ('1X', '1X', round(p_1X, 1))
    elif max_combo == p_X2:
        return ('X2', 'X2', round(p_X2, 1))
    else:
        return ('12', '12', round(p_12, 1))


def validar_acierto(prediccion_codigo: str, resultado_real: str) -> bool:
    """
    Valida si la predicción acertó considerando Doble Oportunidad.
    
    Args:
        prediccion_codigo: 'HOME_WIN', 'AWAY_WIN', 'DRAW', '1X', 'X2', '12'
        resultado_real: 'HOME_WIN', 'AWAY_WIN', 'DRAW'
    
    Returns:
        True si la predicción fue correcta
    """
    # Predicciones simples
    if prediccion_codigo == 'HOME_WIN':
        return resultado_real == 'HOME_WIN'
    
    if prediccion_codigo == 'AWAY_WIN':
        return resultado_real == 'AWAY_WIN'
    
    if prediccion_codigo == 'DRAW':
        return resultado_real == 'DRAW'
    
    # Doble Oportunidad
    if prediccion_codigo == '1X':  # Local o Empate
        return resultado_real in ('HOME_WIN', 'DRAW')
    
    if prediccion_codigo == 'X2':  # Visitante o Empate
        return resultado_real in ('AWAY_WIN', 'DRAW')
    
    if prediccion_codigo == '12':  # Local o Visitante (sin empate)
        return resultado_real in ('HOME_WIN', 'AWAY_WIN')
    
    return False


def evaluar_partidos_finalizados(partidos: list, liga_id: int) -> tuple:
    """
    Evalúa predicciones vs resultados reales para partidos finalizados.
    
    Args:
        partidos: Lista de partidos de la API (status=FINISHED)
        liga_id: ID interno de la liga para cargar datos históricos
    
    Returns:
        tuple: (resultados_evaluados, estadisticas)
    """
    global _cache_fuerzas
    
    resultados = []
    aciertos = 0
    fallos = 0
    sin_prediccion = 0
    
    # Cargar datos históricos (con caché)
    if liga_id not in _cache_fuerzas:
        liga_info = LIGAS.get(liga_id)
        if not liga_info:
            return [], {'error': f'Liga {liga_id} no encontrada'}
        
        try:
            # OPTIMIZADO: Solo cargar columnas necesarias para ahorrar RAM
            columnas_necesarias = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 
                                   'HS', 'AS', 'HC', 'AC', 'HY', 'AY', 'HR', 'AR',
                                   'HST', 'AST', 'HTHG', 'HTAG']
            df = descargar_csv_safe(liga_info.get('url', ''), usecols=columnas_necesarias)
            if df is None or df.empty:
                return [], {'error': 'No se pudieron cargar datos históricos'}
            
            fuerzas, media_local, media_vis = calcular_fuerzas(df)
            equipos = sorted(list(fuerzas.keys()))
            
            _cache_fuerzas[liga_id] = {
                'fuerzas': fuerzas,
                'ml': media_local,
                'mv': media_vis,
                'equipos': equipos,
                'codigo': liga_info.get('codigo', '')
            }
        except Exception as e:
            return [], {'error': f'Error cargando datos: {e}'}
    
    cache = _cache_fuerzas.get(liga_id)
    if not cache:
        return [], {'error': 'Caché vacío'}
    
    fuerzas = cache['fuerzas']
    media_local = cache.get('ml') or cache.get('media_local', 1.5)
    media_vis = cache.get('mv') or cache.get('media_vis', 1.2)
    equipos_validos = cache['equipos']
    league_code = cache.get('codigo', '')
    
    for partido in partidos:
        try:
            # Extraer datos del partido
            home_team = partido.get('homeTeam', {})
            away_team = partido.get('awayTeam', {})
            score = partido.get('score', {})
            
            nombre_local = home_team.get('name', '')
            nombre_visitante = away_team.get('name', '')
            
            # Obtener goles del fullTime
            full_time = score.get('fullTime', {})
            home_goals = full_time.get('home')
            away_goals = full_time.get('away')
            
            # Validar datos
            if not nombre_local or not nombre_visitante:
                continue
            if home_goals is None or away_goals is None:
                continue
            
            # Determinar resultado real
            resultado_real = determinar_resultado_real(home_goals, away_goals)
            
            # Normalizar nombres de equipos
            local_norm, metodo_local, conf_local = _normalizar_nombre_equipo(
                nombre_local, equipos_validos, league_id=league_code
            )
            visitante_norm, metodo_vis, conf_vis = _normalizar_nombre_equipo(
                nombre_visitante, equipos_validos, league_id=league_code
            )
            
            # Verificar que existan en fuerzas
            if local_norm not in fuerzas or visitante_norm not in fuerzas:
                sin_prediccion += 1
                resultados.append({
                    'local': nombre_local,
                    'visitante': nombre_visitante,
                    'goles_local': home_goals,
                    'goles_visitante': away_goals,
                    'resultado_real': resultado_real,
                    'prediccion_ia': None,
                    'prob_local': None,
                    'prob_empate': None,
                    'prob_visitante': None,
                    'acierto': None,
                    'fecha': partido.get('utcDate', '')[:10],
                    'error': 'Equipo no encontrado en BD'
                })
                continue
            
            # Ejecutar predicción
            prediccion = predecir_partido(
                local_norm, visitante_norm,
                fuerzas, media_local, media_vis
            )
            
            if not prediccion:
                sin_prediccion += 1
                continue
            
            # Determinar predicción de la IA (ahora retorna tupla)
            pred_codigo, pred_texto, pred_prob = determinar_prediccion_ia(prediccion)
            
            # Comparar resultado usando la nueva función de validación
            es_acierto = validar_acierto(pred_codigo, resultado_real)
            if es_acierto:
                aciertos += 1
            else:
                fallos += 1
            
            resultados.append({
                'local': nombre_local,
                'visitante': nombre_visitante,
                'goles_local': home_goals,
                'goles_visitante': away_goals,
                'resultado_real': resultado_real,
                'prediccion_ia': pred_codigo,
                'prediccion_texto': pred_texto,
                'prediccion_prob': pred_prob,
                'prob_local': round(prediccion.get('Prob_Local', 0) * 100, 1),
                'prob_empate': round(prediccion.get('Prob_Empate', 0) * 100, 1),
                'prob_visitante': round(prediccion.get('Prob_Vis', 0) * 100, 1),
                'acierto': es_acierto,
                'fecha': partido.get('utcDate', '')[:10],
                'error': None
            })
            
        except Exception as e:
            print(f"⚠️ Error evaluando partido: {e}")
            continue
    
    # Calcular estadísticas
    total_evaluados = aciertos + fallos
    precision = round((aciertos / total_evaluados * 100), 1) if total_evaluados > 0 else 0
    
    estadisticas = {
        'total_partidos': len(partidos),
        'evaluados': total_evaluados,
        'aciertos': aciertos,
        'fallos': fallos,
        'sin_prediccion': sin_prediccion,
        'precision': precision
    }
    
    return resultados, estadisticas


@app.route('/history')
@cache.cached(timeout=120, query_string=True, key_prefix='history_accuracy')
def history():
    """
    Muestra historial de aciertos/fallos de las predicciones.
    Compara predicciones pre-partido con resultados reales.
    
    CACHEADO: 120 segundos (los partidos finalizados no cambian rápido)
    
    Query params:
        - league_code: Código de liga (PL, PD, BL1, etc). Default: PL
        - days: Días hacia atrás (7, 14, 30). Default: 7
    """
    
    # Parámetros GET
    league_code = request.args.get('league_code', 'PL').upper()
    days_back = int(request.args.get('days', 7))
    
    # Validar liga
    if league_code not in LIGAS_HISTORY:
        flash(f"⚠️ Liga '{league_code}' no soportada. Usando Premier League.", "warning")
        league_code = 'PL'
    
    # Validar días
    if days_back not in [7, 14, 30]:
        days_back = 7
    
    liga_info = LIGAS_HISTORY[league_code]
    liga_id = liga_info['liga_id']
    
    resultados = []
    estadisticas = {
        'total_partidos': 0,
        'evaluados': 0,
        'aciertos': 0,
        'fallos': 0,
        'sin_prediccion': 0,
        'precision': 0
    }
    es_demo = False
    
    # Verificar API key
    api_key = os.getenv('FOOTBALL_DATA_API_KEY')
    
    if not api_key:
        flash("⚠️ Configura FOOTBALL_DATA_API_KEY para ver datos reales", "warning")
        es_demo = True
        
        # Datos de ejemplo para demo (con nueva estructura de Doble Oportunidad)
        resultados = [
            {
                'local': 'Arsenal', 'visitante': 'Chelsea',
                'goles_local': 2, 'goles_visitante': 1,
                'resultado_real': 'HOME_WIN', 'prediccion_ia': 'HOME_WIN',
                'prediccion_texto': 'Local', 'prediccion_prob': 52.3,
                'prob_local': 52.3, 'prob_empate': 26.1, 'prob_visitante': 21.6,
                'acierto': True, 'fecha': '2026-01-25', 'error': None
            },
            {
                'local': 'Liverpool', 'visitante': 'Man City',
                'goles_local': 1, 'goles_visitante': 1,
                'resultado_real': 'DRAW', 'prediccion_ia': '1X',
                'prediccion_texto': '1X', 'prediccion_prob': 68.7,
                'prob_local': 38.5, 'prob_empate': 30.2, 'prob_visitante': 31.3,
                'acierto': True, 'fecha': '2026-01-24', 'error': None
            },
            {
                'local': 'Man United', 'visitante': 'Tottenham',
                'goles_local': 0, 'goles_visitante': 2,
                'resultado_real': 'AWAY_WIN', 'prediccion_ia': 'X2',
                'prediccion_texto': 'X2', 'prediccion_prob': 71.3,
                'prob_local': 28.7, 'prob_empate': 25.8, 'prob_visitante': 45.5,
                'acierto': True, 'fecha': '2026-01-23', 'error': None
            },
            {
                'local': 'Newcastle', 'visitante': 'Everton',
                'goles_local': 0, 'goles_visitante': 0,
                'resultado_real': 'DRAW', 'prediccion_ia': '12',
                'prediccion_texto': '12', 'prediccion_prob': 72.0,
                'prob_local': 40.0, 'prob_empate': 28.0, 'prob_visitante': 32.0,
                'acierto': False, 'fecha': '2026-01-22', 'error': None
            },
        ]
        estadisticas = {
            'total_partidos': 4,
            'evaluados': 4,
            'aciertos': 3,
            'fallos': 1,
            'sin_prediccion': 0,
            'precision': 75.0
        }
    
    elif not API_CLIENT_AVAILABLE:
        flash("❌ FootballDataClient no está disponible", "danger")
    
    elif FootballDataClient is not None:
        # MODO PRODUCCIÓN: Obtener partidos reales
        try:
            client = FootballDataClient(api_key)
            partidos = client.get_finished_matches(league_code, days_back=days_back)
            
            if not partidos:
                flash(f"📭 No se encontraron partidos finalizados en los últimos {days_back} días", "info")
            else:
                # Evaluar predicciones
                resultados, estadisticas = evaluar_partidos_finalizados(partidos, liga_id)
                
                if 'error' in estadisticas:
                    flash(f"⚠️ {estadisticas['error']}", "warning")
                    
        except Exception as e:
            error_msg = str(e)
            if '403' in error_msg or 'Forbidden' in error_msg or 'Authorization' in error_msg:
                flash(f"⚠️ Liga '{liga_info['nombre']}' no disponible en plan gratuito de la API. Mostrando datos de ejemplo.", "warning")
                es_demo = True
                # Datos de ejemplo genéricos
                resultados = [
                    {
                        'local': 'Equipo A', 'visitante': 'Equipo B',
                        'goles_local': 2, 'goles_visitante': 1,
                        'resultado_real': 'HOME_WIN', 'prediccion_ia': 'HOME_WIN',
                        'prediccion_texto': 'Local', 'prediccion_prob': 52.3,
                        'prob_local': 52.3, 'prob_empate': 26.1, 'prob_visitante': 21.6,
                        'acierto': True, 'fecha': '2026-01-25', 'error': None
                    },
                ]
                estadisticas = {
                    'total_partidos': 1, 'evaluados': 1, 'aciertos': 1,
                    'fallos': 0, 'sin_prediccion': 0, 'precision': 100.0
                }
            else:
                flash(f"❌ Error obteniendo partidos: {e}", "danger")
                import traceback
                traceback.print_exc()
    
    return render_template('results.html',
                           resultados=resultados,
                           estadisticas=estadisticas,
                           ligas=LIGAS_HISTORY,
                           liga_actual=liga_info,
                           league_code=league_code,
                           days_back=days_back,
                           es_demo=es_demo)


# ============================================================
# MANEJO DE ERRORES
# ============================================================
@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', error="Página no encontrada"), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('base.html', error="Error interno del servidor"), 500


# ============================================================
# SEO: ARCHIVOS ESTÁTICOS EN RAÍZ
# ============================================================
@app.route('/robots.txt')
def robots():
    """Servir robots.txt desde la raíz del dominio."""
    return send_from_directory('static', 'robots.txt')

@app.route('/sitemap.xml')
def sitemap():
    """Servir sitemap.xml desde la raíz del dominio."""
    return send_from_directory('static', 'sitemap.xml')


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print("=" * 50)
    print("🎯 TIMBA PREDICTOR WEB")
    print("=" * 50)
    print(f"📊 Ligas disponibles: {len(LIGAS)}")
    print(f"📅 Fixtures configurados: {len(URLS_FIXTURE)}")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
