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
from datetime import datetime, timedelta, timezone

# ========== IMPORTS LOCALES (desde src/) ==========
from timba_core import (
    LIGAS,
    URLS_FIXTURE,
    calcular_fuerzas,
    predecir_partido,
    obtener_proximos_partidos,
    descargar_csv_safe,
    emparejar_equipo
)

# ========== CONFIGURACIÓN ==========
# Ruta de salida del JSON
OUTPUT_FILE = os.path.join(PROJECT_ROOT, 'data', 'dashboard_cache.json')

# Zona horaria Argentina (UTC-3)
TZ_ARGENTINA = timezone(timedelta(hours=-3))

# Orden de prioridad de ligas (Argentina primero)
ORDEN_LIGAS = [10, 1, 2, 3, 4, 5, 6, 7]

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
    
    if prob_local >= 0.55:
        return f"1 ({round(prob_local * 100)}%)"
    elif prob_vis >= 0.55:
        return f"2 ({round(prob_vis * 100)}%)"
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


def cargar_fuerzas_liga(liga_id: int) -> tuple:
    """
    Descarga CSV histórico y calcula fuerzas de ataque/defensa.
    
    Returns:
        tuple: (fuerzas, media_local, media_vis, equipos_validos) o vacío si falla
    """
    liga_info = LIGAS.get(liga_id)
    if not liga_info:
        return {}, 0, 0, []
    
    try:
        url = liga_info.get('url')
        if not url:
            return {}, 0, 0, []
        
        # Descargar CSV con solo columnas esenciales (ahorra RAM)
        df = descargar_csv_safe(url, usecols=COLUMNAS_ESENCIALES)
        
        if df is None or df.empty:
            log(f"Liga {liga_id}: CSV vacío o nulo", "WARN")
            return {}, 0, 0, []
        
        # Calcular fuerzas (operación CPU-intensiva)
        fuerzas, media_local, media_vis = calcular_fuerzas(df)
        equipos_validos = sorted(list(fuerzas.keys()))
        
        log(f"Liga {liga_id} ({liga_info['nombre'][:30]}...): {len(equipos_validos)} equipos cargados", "OK")
        return fuerzas, media_local, media_vis, equipos_validos
        
    except Exception as e:
        log(f"Liga {liga_id}: Error descargando CSV - {e}", "ERROR")
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
                    
                    # Convertir hora UTC a Argentina
                    hora_local = '--:--'
                    if fecha_utc:
                        try:
                            dt_utc = datetime.fromisoformat(fecha_utc.replace('Z', '+00:00'))
                            dt_arg = dt_utc.astimezone(TZ_ARGENTINA)
                            hora_local = dt_arg.strftime('%H:%M')
                        except:
                            partes = fecha_str.split()
                            hora_local = partes[1] if len(partes) > 1 else '--:--'
                    else:
                        partes = fecha_str.split()
                        hora_local = partes[1] if len(partes) > 1 else '--:--'
                    
                    # Generar predicción
                    prediccion = None
                    recomendacion = None
                    
                    if fuerzas and equipos_validos:
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


def ejecutar_actualizacion():
    """
    Ejecuta ciclo completo de actualización:
    1. Descarga CSVs históricos
    2. Calcula fuerzas
    3. Obtiene fixtures
    4. Genera predicciones
    5. Guarda JSON
    """
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
