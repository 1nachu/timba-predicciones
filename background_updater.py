#!/usr/bin/env python3
"""
Timba Predictor - Background Updater
=====================================

Script independiente para actualizar datos del dashboard en segundo plano.
Ejecuta scraping, cálculos de predicción y guarda resultados en JSON.

Uso:
    python background_updater.py              # Ejecución única
    python background_updater.py --loop 300   # Loop cada 5 minutos

Salida:
    data/dashboard_cache.json

Autor: Timba Team
Última actualización: Febrero 2026
"""

# ========== CONFIGURACIÓN DE PATH ==========
import os
import sys

# Inyectar 'src/' al path ANTES de cualquier import local
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

# ========== IMPORTS ESTÁNDAR ==========
import json
import time
import argparse
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, timezone

# ========== IMPORTS LOCALES (desde src/) ==========
from timba_core import (
    LIGAS,
    URLS_FIXTURE,
    calcular_fuerzas,
    predecir_partido,
    predecir_partido_champions,
    obtener_proximos_partidos,
    descargar_csv_safe,
    emparejar_equipo
)

# ========== CONFIGURACIÓN ==========
# Ruta de salida del JSON
OUTPUT_FILE = os.path.join(PROJECT_ROOT, 'data', 'dashboard_cache.json')

# Auditoría de predicciones
AUDIT_RETENTION_DAYS = 30      # días que se conservan registros de auditoría
AUDIT_FUTURE_DAYS = 7          # días hacia adelante para guardar predicciones
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'databases', 'football_data.db')

# Umbrales de predicción (mantener consistencia con obtener_mejor_recomendacion)
PREDICCION_UMBRAL_GANA = 0.55
PREDICCION_UMBRAL_DOBLE = 0.70

# Zona horaria Argentina (UTC-3)
TZ_ARGENTINA = timezone(timedelta(hours=-3))

# Orden de prioridad de ligas (Argentina primero)
ORDEN_LIGAS = [10, 1, 2, 3, 4, 5, 6, 7, 8]

# Cache de fuerzas usada por auditoría
cache_fuerzas = {}

# Columnas esenciales para ahorrar RAM al descargar CSVs
COLUMNAS_ESENCIALES = [
    'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG',
    'HS', 'AS', 'HC', 'AC', 'HY', 'AY', 'HR', 'AR',
    'HST', 'AST', 'HTHG', 'HTAG'
]


def log(mensaje: str, nivel: str = "INFO"):
    """Logger simple con timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    iconos = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERROR": "❌", "START": "🚀"}
    print(f"[{timestamp}] {iconos.get(nivel, 'ℹ️')} {mensaje}")


def obtener_mejor_recomendacion(prediccion: dict) -> str:
    """Genera recomendación simple basada en probabilidades."""
    prob_local = prediccion.get('Prob_Local', 0)
    prob_empate = prediccion.get('Prob_Empate', 0)
    prob_vis = prediccion.get('Prob_Vis', 0)
    
    if prob_local >= PREDICCION_UMBRAL_GANA:
        return f"1 ({round(prob_local * 100)}%)"
    elif prob_vis >= PREDICCION_UMBRAL_GANA:
        return f"2 ({round(prob_vis * 100)}%)"
    elif prediccion.get('Prob_1X', 0) >= PREDICCION_UMBRAL_DOBLE:
        return "1X"
    elif prediccion.get('Prob_X2', 0) >= PREDICCION_UMBRAL_DOBLE:
        return "X2"
    elif prediccion.get('Over_25', 0) >= 0.65:
        return "Over 2.5"
    elif prediccion.get('Over_15', 0) >= 0.75:
        return "Over 1.5"
    else:
        return "—"


def determinar_prediccion_1x2(prediccion: dict) -> str:
    """Determina el código 1X2 basado en las probabilidades de la predicción.

    Usa los mismos umbrales que obtener_mejor_recomendacion().
    """
    prob_local = prediccion.get('Prob_Local', 0)
    prob_empate = prediccion.get('Prob_Empate', 0)
    prob_vis = prediccion.get('Prob_Vis', 0)

    if prob_local >= PREDICCION_UMBRAL_GANA:
        return 'HOME_WIN'
    if prob_vis >= PREDICCION_UMBRAL_GANA:
        return 'AWAY_WIN'

    if prediccion.get('Prob_1X', 0) >= PREDICCION_UMBRAL_DOBLE:
        return '1X'
    if prediccion.get('Prob_X2', 0) >= PREDICCION_UMBRAL_DOBLE:
        return 'X2'
    if prediccion.get('Prob_12', 0) >= PREDICCION_UMBRAL_DOBLE:
        return '12'

    # Default: el más probable entre las 3 opciones simples
    valores = {
        'HOME_WIN': prob_local,
        'DRAW': prob_empate,
        'AWAY_WIN': prob_vis
    }
    return max(valores, key=valores.get)


def cargar_fuerzas_liga(liga_id: int) -> tuple:
    """
    Obtiene datos históricos desde BD local (con fallback a CSV) y calcula fuerzas.
    
    Returns:
        tuple: (fuerzas, media_local, media_vis, equipos_validos) o vacío si falla
    """
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
            log(f"Liga {liga_id}: Datos vacíos", "WARN")
            return {}, 0, 0, []
        
        # Calcular fuerzas
        fuerzas, media_local, media_vis = calcular_fuerzas(df)
        equipos_validos = sorted(list(fuerzas.keys()))
        
        log(f"Liga {liga_id} ({liga_info.get('nombre', codigo)[:30]}...): {len(equipos_validos)} equipos cargados", "OK")
        return fuerzas, media_local, media_vis, equipos_validos
        
    except Exception as e:
        log(f"Liga {liga_id}: Error cargando datos - {e}", "ERROR")
        return {}, 0, 0, []


def obtener_fixtures_liga(liga_id: int) -> list:
    """
    Descarga próximos partidos de una liga.
    
    Returns:
        list: Lista de partidos raw o vacía si falla
    """
    fixture_data = URLS_FIXTURE.get(liga_id, {})
    url_fixture = fixture_data.get('url')
    
    if not url_fixture:
        return []
    
    try:
        partidos = obtener_proximos_partidos(url_fixture)
        log(f"Liga {liga_id}: {len(partidos)} fixtures descargados", "OK")
        return partidos
    except Exception as e:
        log(f"Liga {liga_id}: Error obteniendo fixtures - {e}", "ERROR")
        return []


def procesar_partidos_hoy(cache_fuerzas: dict) -> list:
    """
    Procesa partidos de hoy de todas las ligas y genera predicciones.
    
    Args:
        cache_fuerzas: Dict con fuerzas pre-calculadas por liga_id
    
    Returns:
        list: Lista de partidos procesados con predicciones
    """
    ahora_arg = datetime.now(TZ_ARGENTINA)
    hoy = ahora_arg.date()
    
    partidos_hoy = []
    
    # Iterar ligas en orden de prioridad
    ligas_ordenadas = [(lid, URLS_FIXTURE[lid]) for lid in ORDEN_LIGAS if lid in URLS_FIXTURE]
    
    for liga_id, fixture_data in ligas_ordenadas:
        liga_info = LIGAS.get(liga_id, {})
        liga_nombre = liga_info.get('nombre', fixture_data.get('liga', f'Liga {liga_id}'))
        
        try:
            # Obtener fixtures de la liga
            partidos_raw = obtener_fixtures_liga(liga_id)
            
            # Obtener fuerzas desde caché
            fuerzas, media_local, media_vis, equipos_validos = cache_fuerzas.get(
                liga_id, ({}, 0, 0, [])
            )
            
            for p in partidos_raw:
                fecha_str = p.get('fecha', '')
                fecha_utc = p.get('fecha_utc', '')
                
                try:
                    if not fecha_str or fecha_str == 'Próximo':
                        continue
                    
                    # Parsear fecha
                    fecha_partido = datetime.strptime(fecha_str.split()[0], '%Y-%m-%d').date()
                    
                    if fecha_partido != hoy:
                        continue
                    
                    # Calcular fecha_utc_real corregida para mostrar hora local en el frontend
                    fecha_utc_real = None
                    if fecha_utc:
                        try:
                            if liga_id == 10:
                                # Promiedos devuelve hora argentina con Z (incorrecto)
                                # Corregimos sumando 3 horas para obtener UTC real
                                dt_arg = datetime.fromisoformat(fecha_utc.replace('Z', ''))
                                dt_utc_real = dt_arg + timedelta(hours=3)
                                fecha_utc_real = dt_utc_real.strftime('%Y-%m-%dT%H:%M:%SZ')
                            else:
                                # Otras ligas ya vienen con el UTC correcto
                                fecha_utc_real = fecha_utc
                        except:
                            pass
                        
                    # Fallback: hora directa de fecha_str (ya es hora argentina)
                    partes = fecha_str.split()
                    hora_local = partes[1] if len(partes) > 1 else '--:--'


                    
                    # Generar predicción
                    prediccion = None
                    recomendacion = None

                    if liga_id == 8:
                        # Champions: usar fuerzas de ligas domésticas pre-cargadas
                        try:
                            pred = predecir_partido_champions(
                                p['local'], p['visitante'], cache_fuerzas
                            )
                            if pred:
                                prediccion = {
                                    'local': round(pred.get('Prob_Local', 0) * 100, 1),
                                    'empate': round(pred.get('Prob_Empate', 0) * 100, 1),
                                    'visitante': round(pred.get('Prob_Vis', 0) * 100, 1)
                                }
                                recomendacion = obtener_mejor_recomendacion(pred)
                        except Exception as e:
                            log(f"Error predicción Champions {p['local']} vs {p['visitante']}: {e}", "WARN")
                    elif fuerzas and equipos_validos:
                        try:
                            # Normalizar nombres de equipos
                            local_match = emparejar_equipo(p['local'], equipos_validos)
                            vis_match = emparejar_equipo(p['visitante'], equipos_validos)
                            
                            if local_match in fuerzas and vis_match in fuerzas:
                                pred = predecir_partido(
                                    local_match, vis_match,
                                    fuerzas, media_local, media_vis
                                )
                                
                                if pred:
                                    prediccion = {
                                        'local': round(pred.get('Prob_Local', 0) * 100, 1),
                                        'empate': round(pred.get('Prob_Empate', 0) * 100, 1),
                                        'visitante': round(pred.get('Prob_Vis', 0) * 100, 1)
                                    }
                                    recomendacion = obtener_mejor_recomendacion(pred)
                        except Exception as e:
                            log(f"Error predicción {p['local']} vs {p['visitante']}: {e}", "WARN")
                    
                    # Agregar partido procesado
                    partidos_hoy.append({
                        'liga_id': liga_id,
                        'liga_nombre': liga_nombre,
                        'local': p['local'],
                        'visitante': p['visitante'],
                        'fecha': fecha_str,
                        'hora': hora_local,
                        'fecha_utc': fecha_utc_real,
                        'prediccion': prediccion,
                        'recomendacion': recomendacion
                    })
                    
                except (ValueError, IndexError) as e:
                    continue
                    
        except Exception as e:
            log(f"Error procesando liga {liga_nombre}: {e}", "ERROR")
            continue
    
    return partidos_hoy


def agrupar_por_liga(partidos: list) -> dict:
    """Agrupa partidos por liga manteniendo el orden de prioridad."""
    partidos_por_liga = {}
    
    for p in partidos:
        lid = p['liga_id']
        if lid not in partidos_por_liga:
            partidos_por_liga[lid] = {
                'nombre': p['liga_nombre'],
                'partidos': []
            }
        partidos_por_liga[lid]['partidos'].append(p)
    
    # Ordenar según prioridad
    partidos_ordenados = {}
    for lid in ORDEN_LIGAS:
        if lid in partidos_por_liga:
            partidos_ordenados[lid] = partidos_por_liga[lid]
    
    return partidos_ordenados


def guardar_cache(datos: dict):
    """Guarda datos en archivo JSON."""
    # Asegurar que existe el directorio
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    
    log(f"Cache guardado: {OUTPUT_FILE}", "OK")


def init_audit_db():
    """Inicializa la base de datos de auditoría si no existe."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT NOT NULL,
            liga_id INTEGER NOT NULL,
            liga_nombre TEXT NOT NULL,
            local TEXT NOT NULL,
            visitante TEXT NOT NULL,
            local_csv TEXT NOT NULL,
            visitante_csv TEXT NOT NULL,
            fecha_partido TEXT NOT NULL,
            fecha_solo TEXT NOT NULL,
            prob_local REAL,
            prob_empate REAL,
            prob_visitante REAL,
            prediccion_1x2 TEXT,
            prob_over_15 REAL,
            prob_over_25 REAL,
            prob_under_35 REAL,
            prob_btts REAL,
            prob_1x REAL,
            prob_x2 REAL,
            prob_12 REAL,
            xg_local REAL,
            xg_visitante REAL,
            prob_over_85_corners REAL,
            prob_over_95_corners REAL,
            prob_over_25_cards REAL,
            prob_over_35_cards REAL,
            resultado_real TEXT,
            goles_local INTEGER,
            goles_visitante INTEGER,
            resultado_registrado_at TEXT,
            acierto_1x2 INTEGER,
            guardado_at TEXT NOT NULL,
            UNIQUE(match_id)
        )
    """)

    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_audit_fecha ON predictions_audit(fecha_partido)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_audit_liga ON predictions_audit(liga_id)""")
    cursor.execute(
        """CREATE INDEX IF NOT EXISTS idx_audit_pendiente ON predictions_audit(resultado_real)
           WHERE resultado_real IS NULL"""
    )

    conn.commit()
    conn.close()


def limpiar_audit_viejo():
    """Elimina registros de auditoría más viejos que AUDIT_RETENTION_DAYS."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM predictions_audit "
        "WHERE fecha_partido < datetime('now', ? || ' days')",
        (f'-{AUDIT_RETENTION_DAYS}',)
    )
    conn.commit()
    conn.close()


def guardar_prediccion_audit(partido: dict, prediccion: dict, liga_id: int, liga_nombre: str):
    """Guarda en la tabla de auditoría la predicción pre-partido."""
    # Obtener lista de equipos normalizados (CSV) desde el cache de fuerzas
    fuerzas, media_local, media_vis, equipos_validos = cache_fuerzas.get(
        liga_id, ({}, 0, 0, [])
    )

    local = partido.get('local', '')
    visitante = partido.get('visitante', '')

    local_csv = emparejar_equipo(local, equipos_validos) if equipos_validos else local
    visitante_csv = emparejar_equipo(visitante, equipos_validos) if equipos_validos else visitante

    fecha_utc = partido.get('fecha_utc')
    fecha_str = partido.get('fecha', '')
    fecha_dt = None

    if fecha_utc:
        try:
            fecha_dt = datetime.fromisoformat(fecha_utc.replace('Z', '+00:00'))
            if fecha_dt.tzinfo is not None:
                fecha_dt = fecha_dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            fecha_dt = None

    if fecha_dt is None and fecha_str:
        try:
            fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M')
        except Exception:
            try:
                fecha_dt = datetime.strptime(fecha_str.split()[0], '%Y-%m-%d')
            except Exception:
                fecha_dt = None

    if not fecha_dt:
        return

    # Convertir a UTC y formato ISO
    fecha_partido = fecha_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    fecha_solo = fecha_dt.strftime('%Y-%m-%d')

    # Guardar solo si el partido no comenzó aún
    if fecha_dt <= datetime.utcnow():
        return

    match_id = f"{liga_id}_{local_csv}_{visitante_csv}_{fecha_solo}"
    prediccion_1x2 = determinar_prediccion_1x2(prediccion) if prediccion else None
    pred = prediccion or {}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """INSERT OR IGNORE INTO predictions_audit (
            match_id, liga_id, liga_nombre, local, visitante,
            local_csv, visitante_csv, fecha_partido, fecha_solo,
            prob_local, prob_empate, prob_visitante,
            prediccion_1x2, prob_over_15, prob_over_25, prob_under_35,
            prob_btts, prob_1x, prob_x2, prob_12,
            xg_local, xg_visitante,
            prob_over_85_corners, prob_over_95_corners,
            prob_over_25_cards, prob_over_35_cards,
            guardado_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            match_id,
            liga_id,
            liga_nombre,
            local,
            visitante,
            local_csv,
            visitante_csv,
            fecha_partido,
            fecha_solo,
            pred.get('Prob_Local'),
            pred.get('Prob_Empate'),
            pred.get('Prob_Vis'),
            prediccion_1x2,
            pred.get('Over_15'),
            pred.get('Over_25'),
            pred.get('Under_35'),
            pred.get('BTTS'),
            pred.get('Prob_1X'),
            pred.get('Prob_X2'),
            pred.get('Prob_12'),
            pred.get('xG_Local'),
            pred.get('xG_Vis'),
            pred.get('Over_85'),
            pred.get('Over_95'),
            pred.get('Over_25_Cards'),
            pred.get('Over_35_Cards'),
            datetime.utcnow().isoformat() + 'Z'
        )
    )

    conn.commit()
    conn.close()


def procesar_proximos_n_dias(cache_fuerzas: dict, dias: int):
    """Procesa predicciones para los próximos N días y guarda en la auditoría."""
    hoy = datetime.utcnow().date()
    hasta = hoy + timedelta(days=dias)

    for liga_id in ORDEN_LIGAS:
        liga_info = LIGAS.get(liga_id, {})
        liga_nombre = liga_info.get('nombre', f'Liga {liga_id}')

        try:
            partidos_raw = obtener_fixtures_liga(liga_id)
            fuerzas, media_local, media_vis, equipos_validos = cache_fuerzas.get(
                liga_id, ({}, 0, 0, [])
            )

            for p in partidos_raw:
                fecha_str = p.get('fecha', '')
                fecha_utc = p.get('fecha_utc', '')

                # Determinar fecha UTC del partido
                fecha_dt = None
                if fecha_utc:
                    try:
                        fecha_dt = datetime.fromisoformat(fecha_utc.replace('Z', '+00:00'))
                        if fecha_dt.tzinfo is not None:
                            fecha_dt = fecha_dt.astimezone(timezone.utc).replace(tzinfo=None)
                    except Exception:
                        fecha_dt = None

                if fecha_dt is None and fecha_str:
                    try:
                        fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M')
                    except Exception:
                        try:
                            fecha_dt = datetime.strptime(fecha_str.split()[0], '%Y-%m-%d')
                        except Exception:
                            fecha_dt = None

                if not fecha_dt:
                    continue

                if not (hoy <= fecha_dt.date() <= hasta):
                    continue

                # Generar predicción
                if liga_id == 8:
                    # Champions: usar fuerzas de ligas domésticas pre-cargadas
                    try:
                        pred = predecir_partido_champions(
                            p['local'], p['visitante'], cache_fuerzas
                        )
                        if pred:
                            guardar_prediccion_audit(p, pred, liga_id, liga_nombre)
                    except Exception as e:
                        log(f"Error guardando auditoría Champions {liga_nombre}: {e}", "WARN")
                elif fuerzas and equipos_validos:
                    try:
                        local_match = emparejar_equipo(p['local'], equipos_validos)
                        vis_match = emparejar_equipo(p['visitante'], equipos_validos)
                        if local_match in fuerzas and vis_match in fuerzas:
                            pred = predecir_partido(
                                local_match, vis_match, fuerzas, media_local, media_vis
                            )
                            if pred:
                                guardar_prediccion_audit(p, pred, liga_id, liga_nombre)
                    except Exception as e:
                        log(f"Error guardando auditoría {liga_nombre}: {e}", "WARN")

        except Exception as e:
            log(f"Error procesando próximos días para liga {liga_nombre}: {e}", "ERROR")


def registrar_resultados_desde_csv(cache_fuerzas: dict):
    """Registra resultados reales en la tabla de auditoría cargando CSV de football-data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for liga_id, liga_info in LIGAS.items():
        url = liga_info.get('url')
        if not url:
            continue

        try:
            df = descargar_csv_safe(url, usecols=['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'])
            if df is None or df.empty:
                continue

            df.columns = df.columns.str.strip()
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'])

            for _, row in df.iterrows():
                fecha_solo = row['Date'].strftime('%Y-%m-%d')

                # Normalizar nombres según CSV de la liga para que el match_id coincida
                equipos_validos = cache_fuerzas.get(liga_id, ({}, 0, 0, []))[3]
                local_csv = emparejar_equipo(str(row['HomeTeam']), equipos_validos) if equipos_validos else str(row['HomeTeam'])
                visitante_csv = emparejar_equipo(str(row['AwayTeam']), equipos_validos) if equipos_validos else str(row['AwayTeam'])

                match_id = f"{liga_id}_{local_csv}_{visitante_csv}_{fecha_solo}"

                cursor.execute(
                    "SELECT prediccion_1x2 FROM predictions_audit "
                    "WHERE match_id = ? AND resultado_real IS NULL",
                    (match_id,)
                )
                found = cursor.fetchone()
                if not found:
                    continue

                prediccion_1x2 = found[0]
                goles_local = int(row['FTHG'])
                goles_visitante = int(row['FTAG'])

                if goles_local > goles_visitante:
                    resultado_real = 'HOME_WIN'
                elif goles_local < goles_visitante:
                    resultado_real = 'AWAY_WIN'
                else:
                    resultado_real = 'DRAW'

                # Calcular acierto según doble oportunidad
                acierto = None
                if prediccion_1x2 == 'HOME_WIN':
                    acierto = 1 if resultado_real == 'HOME_WIN' else 0
                elif prediccion_1x2 == 'AWAY_WIN':
                    acierto = 1 if resultado_real == 'AWAY_WIN' else 0
                elif prediccion_1x2 == 'DRAW':
                    acierto = 1 if resultado_real == 'DRAW' else 0
                elif prediccion_1x2 == '1X':
                    acierto = 1 if resultado_real in ('HOME_WIN', 'DRAW') else 0
                elif prediccion_1x2 == 'X2':
                    acierto = 1 if resultado_real in ('AWAY_WIN', 'DRAW') else 0
                elif prediccion_1x2 == '12':
                    acierto = 1 if resultado_real in ('HOME_WIN', 'AWAY_WIN') else 0

                cursor.execute(
                    """UPDATE predictions_audit SET 
                       resultado_real = ?, goles_local = ?, goles_visitante = ?,
                       resultado_registrado_at = ?, acierto_1x2 = ?
                       WHERE match_id = ?""",
                    (
                        resultado_real,
                        goles_local,
                        goles_visitante,
                        datetime.utcnow().isoformat() + 'Z',
                        acierto,
                        match_id,
                    )
                )

            conn.commit()

        except Exception as e:
            log(f"Error registrando resultados CSV para liga {liga_id}: {e}", "ERROR")

    conn.close()


def ejecutar_actualizacion():
    """
    Ejecuta ciclo completo de actualización:
    1. Descarga CSVs históricos
    2. Calcula fuerzas
    3. Obtiene fixtures
    4. Genera predicciones
    5. Guarda JSON
    """
    global cache_fuerzas

    log("Iniciando actualización de datos...", "START")
    inicio = time.time()
    
    # PASO 1: Pre-cargar fuerzas de todas las ligas
    log("Paso 1/3: Descargando datos históricos y calculando fuerzas...")
    cache_fuerzas = {}
    
    for liga_id in ORDEN_LIGAS:
        if liga_id not in LIGAS:
            continue
        try:
            fuerzas, media_local, media_vis, equipos = cargar_fuerzas_liga(liga_id)
            cache_fuerzas[liga_id] = (fuerzas, media_local, media_vis, equipos)
        except Exception as e:
            log(f"Fallo cargando liga {liga_id}: {e}", "ERROR")
            cache_fuerzas[liga_id] = ({}, 0, 0, [])
    
    # PASO 2: Procesar partidos de hoy
    log("Paso 2/3: Obteniendo fixtures y generando predicciones...")
    partidos_hoy = procesar_partidos_hoy(cache_fuerzas)
    
    # PASO 3: Agrupar y guardar
    log("Paso 3/3: Guardando cache...")
    partidos_agrupados = agrupar_por_liga(partidos_hoy)
    
    datos_cache = {
        'updated_at': datetime.now(TZ_ARGENTINA).isoformat(),
        'total_ligas': len(LIGAS),
        'total_partidos_hoy': len(partidos_hoy),
        'partidos_hoy': partidos_agrupados,
        'ligas': {str(k): v for k, v in LIGAS.items()}  # Convertir keys a string para JSON
    }
    
    guardar_cache(datos_cache)

    # Auditoría de predicciones: crear DB, limpiar viejo, guardar próximos, registrar resultados
    try:
        init_audit_db()
        limpiar_audit_viejo()
        procesar_proximos_n_dias(cache_fuerzas, AUDIT_FUTURE_DAYS)
        registrar_resultados_desde_csv(cache_fuerzas)
    except Exception as e:
        log(f"Error en auditoría de predicciones: {e}", "ERROR")

    duracion = time.time() - inicio
    log(f"Actualización completada en {duracion:.1f}s - {len(partidos_hoy)} partidos procesados", "OK")
    
    return datos_cache


def main():
    """Punto de entrada principal con soporte para modo loop."""
    parser = argparse.ArgumentParser(description='Timba Background Updater')
    parser.add_argument(
        '--loop', 
        type=int, 
        default=0,
        help='Intervalo en segundos para ejecutar en loop (0 = ejecución única)'
    )
    args = parser.parse_args()
    
    if args.loop > 0:
        log(f"Modo loop activado: actualización cada {args.loop} segundos", "INFO")
        while True:
            try:
                ejecutar_actualizacion()
            except Exception as e:
                log(f"Error en ciclo de actualización: {e}", "ERROR")
            
            log(f"Esperando {args.loop} segundos hasta próxima actualización...", "INFO")
            time.sleep(args.loop)
    else:
        # Ejecución única
        ejecutar_actualizacion()


if __name__ == '__main__':
    main()
