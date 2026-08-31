"""
Fixtures Service
================
Servicio para normalización de nombres, ordenamiento, filtrado y enriquecimiento de partidos.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from utils.shared import get_db_connection, LIVE_SCORES_DB_PATH, emparejar_equipo
from timba_core import LIGAS, predecir_partido, predecir_partido_champions, calcular_fuerzas, descargar_csv_safe

try:
    from team_normalization import TeamNormalizer
    TEAM_NORMALIZER_AVAILABLE = True
except ImportError:
    TeamNormalizer = None
    TEAM_NORMALIZER_AVAILABLE = False

logger = logging.getLogger(__name__)

# Prioridad visual de ligas
LIGA_PRIORIDAD = {
    'PL': 1, 'E0': 1,
    'BL1': 2, 'D1': 2,
    'PD': 3, 'SP1': 3,
    'SA': 4, 'I1': 4,
    'FL1': 5, 'F1': 5,
    'PPL': 6, 'P1': 6,
    'DED': 7, 'N1': 7,
    'ARG': 8,
    'CL': 9
}

API_TO_LIGA_ID = {
    'PL': 1,
    'PD': 2,
    'SA': 3,
    'BL1': 4,
    'FL1': 5,
    'PPL': 6,
    'DED': 7,
    'CL': 8,
}

API_TO_LEAGUE_CODE = {
    'PL': 'E0',
    'PD': 'SP1',
    'SA': 'I1',
    'BL1': 'D1',
    'FL1': 'F1',
    'PPL': 'P1',
    'DED': 'N1',
}

_team_normalizer = None
_cache_fuerzas = {}


def get_team_normalizer():
    """Obtiene o inicializa el singleton de TeamNormalizer."""
    global _team_normalizer
    if _team_normalizer is None and TEAM_NORMALIZER_AVAILABLE and TeamNormalizer is not None:
        try:
            _team_normalizer = TeamNormalizer()
        except Exception as e:
            logger.warning(f"No se pudo inicializar TeamNormalizer: {e}")
    return _team_normalizer


def normalizar_nombre_equipo(nombre_api: str, equipos_validos: list, league_id: Optional[str] = None) -> tuple:
    """
    Normaliza un nombre de equipo usando la BD de aliases o fuzzy matching directo.
    Returns: (nombre_normalizado, metodo_usado, confianza)
    """
    normalizer = get_team_normalizer()
    
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
        except Exception:
            pass
            
    match = emparejar_equipo(nombre_api, equipos_validos)
    if match in equipos_validos:
        return (match, 'fuzzy', 80.0)
        
    return (nombre_api, 'none', 0.0)


def ordenar_partidos_por_liga(partidos: list) -> list:
    """Ordena partidos por prioridad de liga."""
    def get_prioridad(partido):
        try:
            if isinstance(partido, dict):
                comp = partido.get('competition', {})
                if isinstance(comp, dict):
                    codigo = comp.get('code', '')
                    return LIGA_PRIORIDAD.get(codigo, 999)
            return 999
        except Exception:
            return 999
    return sorted(partidos, key=get_prioridad)


def limpiar_partidos_viejos() -> int:
    """Elimina snapshots y eventos con más de 24 horas de antigüedad."""
    db_path = LIVE_SCORES_DB_PATH
    if not os.path.exists(str(db_path)):
        return 0
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        limite_24h = (datetime.now() - timedelta(hours=24)).timestamp()
        cursor.execute("DELETE FROM match_snapshots WHERE timestamp < ?", (limite_24h,))
        deleted = cursor.rowcount
        cursor.execute("DELETE FROM match_events WHERE timestamp < ?", (limite_24h,))
        conn.commit()
        conn.close()
        return deleted
    except Exception as e:
        logger.error(f"Error limpiando DB de live scores: {e}")
        return 0


def obtener_partidos_locales() -> list:
    """Lee partidos en vivo y programados del día desde live_scores.db."""
    db_path = LIVE_SCORES_DB_PATH
    partidos = []
    if not os.path.exists(str(db_path)):
        return []
    try:
        conn = get_db_connection(db_path, readonly=True)
        cursor = conn.cursor()
        ahora = datetime.now()

        cursor.execute("""
            SELECT data, 'live' as seccion FROM match_snapshots 
            WHERE status IN ('LIVE', 'IN_PLAY', 'PAUSED', 'HALFTIME')
            ORDER BY timestamp ASC
            LIMIT 20
        """)
        rows_live = cursor.fetchall()

        cursor.execute("""
            SELECT data, 'proximos' as seccion FROM match_snapshots 
            WHERE status IN ('TIMED', 'SCHEDULED')
            AND json_extract(data, '$.utcDate') >= ?
            AND json_extract(data, '$.utcDate') < ?
            ORDER BY json_extract(data, '$.utcDate') ASC
            LIMIT 30
        """, (
            datetime(ahora.year, ahora.month, ahora.day, 0, 0, 0).isoformat(),
            datetime(ahora.year, ahora.month, ahora.day + 1, 0, 0, 0).isoformat()
        ))
        rows_proximos = cursor.fetchall()
        rows = rows_live + rows_proximos

        for row in rows:
            try:
                snap = json.loads(row[0])
                seccion = row[1]
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
                    'homeTeam': {'name': snap['home_team']},
                    'awayTeam': {'name': snap['away_team']},
                    'utcDate': snap.get('utcDate', datetime.fromtimestamp(snap.get('timestamp', ahora.timestamp())).isoformat()),
                    '_timestamp': snap.get('timestamp', 0),
                    'seccion': seccion
                }
                partidos.append(partido)
            except Exception:
                continue
        conn.close()
        return partidos
    except Exception as e:
        logger.error(f"Error leyendo partidos locales: {e}")
        return []


def enriquecer_partidos_con_prediccion(partidos: list, cache_service=None) -> list:
    """Enriquece cada partido con probabilidades del motor Timba."""
    global _cache_fuerzas
    for partido in partidos:
        partido['prediccion_timba'] = None
        try:
            comp = partido.get('competition', {})
            api_code = comp.get('code', '') if isinstance(comp, dict) else ''
            if api_code not in API_TO_LIGA_ID:
                continue
            liga_id = API_TO_LIGA_ID[api_code]

            if api_code == 'CL':
                if cache_service:
                    cache_todas = {lid: cache_service.cargar_datos_liga_cached(lid) for lid in LIGAS if LIGAS[lid].get('url')}
                    pred = predecir_partido_champions(partido['homeTeam']['name'], partido['awayTeam']['name'], cache_todas)
                    if pred:
                        partido['prediccion_timba'] = {
                            'prob_local': round(pred.get('Prob_Local', 0) * 100, 1),
                            'prob_empate': round(pred.get('Prob_Empate', 0) * 100, 1),
                            'prob_visitante': round(pred.get('Prob_Vis', 0) * 100, 1),
                        }
                continue

            if liga_id not in _cache_fuerzas:
                liga_info = LIGAS.get(liga_id)
                if liga_info and liga_info.get('url'):
                    cols = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'HS', 'AS', 'HC', 'AC', 'HY', 'AY', 'HR', 'AR', 'HST', 'AST', 'HTHG', 'HTAG']
                    df = descargar_csv_safe(liga_info.get('url'), usecols=cols)
                    if df is not None and not df.empty:
                        fuerzas, ml, mv = calcular_fuerzas(df)
                        _cache_fuerzas[liga_id] = {'fuerzas': fuerzas, 'ml': ml, 'mv': mv, 'equipos': sorted(list(fuerzas.keys()))}

            cache = _cache_fuerzas.get(liga_id)
            if not cache:
                continue

            home_name = partido['homeTeam']['name']
            away_name = partido['awayTeam']['name']
            league_code = API_TO_LEAGUE_CODE.get(api_code)

            local_norm, _, _ = normalizar_nombre_equipo(home_name, cache['equipos'], league_id=league_code)
            vis_norm, _, _ = normalizar_nombre_equipo(away_name, cache['equipos'], league_id=league_code)

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
        except Exception:
            continue
    return partidos
