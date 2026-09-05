"""
Audit Service
=============
Servicio para evaluación de precisión, validación de aciertos y consulta histórica de predicciones.
"""

import logging
from typing import Dict, List, Tuple, Optional
from utils.shared import get_db_connection, DB_PATH
from utils.markets import determinar_prediccion_1x2, PREDICCION_UMBRAL_GANA, PREDICCION_UMBRAL_DOBLE

logger = logging.getLogger(__name__)


def determinar_resultado_real(home_goals: int, away_goals: int) -> str:
    """
    Determina el resultado real basado en los goles.
    Returns: 'HOME_WIN', 'DRAW' o 'AWAY_WIN'
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
    Returns: (prediccion_codigo, texto_display, probabilidad_display)
    """
    prob_local = prediccion.get('Prob_Local', 0)
    prob_empate = prediccion.get('Prob_Empate', 0)
    prob_vis = prediccion.get('Prob_Vis', 0)
    
    pl_pct = prob_local * 100
    pe_pct = prob_empate * 100
    pv_pct = prob_vis * 100
    
    if pl_pct > 50:
        return ('HOME_WIN', 'Local', round(pl_pct, 1))
    if pv_pct > 50:
        return ('AWAY_WIN', 'Visitante', round(pv_pct, 1))
    
    p_1X = pl_pct + pe_pct
    p_X2 = pv_pct + pe_pct
    p_12 = pl_pct + pv_pct
    
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
    """
    if prediccion_codigo == 'HOME_WIN':
        return resultado_real == 'HOME_WIN'
    if prediccion_codigo == 'AWAY_WIN':
        return resultado_real == 'AWAY_WIN'
    if prediccion_codigo == 'DRAW':
        return resultado_real == 'DRAW'
    if prediccion_codigo == '1X':
        return resultado_real in ('HOME_WIN', 'DRAW')
    if prediccion_codigo == 'X2':
        return resultado_real in ('AWAY_WIN', 'DRAW')
    if prediccion_codigo == '12':
        return resultado_real in ('HOME_WIN', 'AWAY_WIN')
    return False


def sincronizar_resultados_audit(db_path=DB_PATH) -> int:
    """
    Sincroniza y registra resultados reales en predictions_audit desde múltiples fuentes:
    1. Feeds JSON de FixtureDownload (contiene marcadores finales)
    2. Tabla histórica local 'matches' en SQLite
    3. Descarga CSV de football-data (si está disponible)
    """
    import requests
    from datetime import datetime, timezone
    from config.leagues import LIGAS, URLS_FIXTURE

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Obtener predicciones pendientes que ya debieron haberse jugado
    cursor.execute(
        """
        SELECT match_id, liga_id, local, visitante, local_csv, visitante_csv, fecha_solo, prediccion_1x2
        FROM predictions_audit
        WHERE resultado_real IS NULL
        """
    )
    pendientes = cursor.fetchall()
    if not pendientes:
        conn.close()
        return 0

    actualizados = 0

    # Fuente 1: Feeds de FixtureDownload
    for liga_id, info in URLS_FIXTURE.items():
        url = info.get('url', '')
        if not url or 'fixturedownload.com' not in url:
            continue
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}, timeout=6)
            if r.status_code != 200:
                continue
            data = r.json()
            for f in data:
                hs = f.get('HomeTeamScore')
                as_ = f.get('AwayTeamScore')
                if hs is None or as_ is None:
                    continue
                date_utc = f.get('DateUtc', '')
                f_date = date_utc[:10] if date_utc else ''
                home = str(f.get('HomeTeam', '')).strip().lower()
                away = str(f.get('AwayTeam', '')).strip().lower()

                for p in pendientes:
                    p_id, p_liga, p_loc, p_vis, p_loc_csv, p_vis_csv, p_fecha, p_pred = p
                    if p_liga != liga_id:
                        continue

                    # Coincidencia por fecha y nombres de equipos
                    loc_match = (p_loc or '').lower() == home or (p_loc_csv or '').lower() == home
                    vis_match = (p_vis or '').lower() == away or (p_vis_csv or '').lower() == away

                    if p_fecha == f_date and (loc_match or vis_match):
                        res_real = determinar_resultado_real(int(hs), int(as_))
                        acierto = 1 if validar_acierto(p_pred, res_real) else 0
                        cursor.execute(
                            """UPDATE predictions_audit SET
                               resultado_real = ?, goles_local = ?, goles_visitante = ?,
                               resultado_registrado_at = ?, acierto_1x2 = ?
                               WHERE match_id = ? AND resultado_real IS NULL""",
                            (res_real, int(hs), int(as_), datetime.now(timezone.utc).isoformat() + 'Z', acierto, p_id)
                        )
                        actualizados += cursor.rowcount
        except Exception as e:
            logger.debug(f"Error sincronizando fixtures de liga {liga_id}: {e}")

    # Fuente 2: Tabla local matches
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='matches'")
        if cursor.fetchone():
            cursor.execute("SELECT league_code, date, home_team, away_team, fthg, ftag FROM matches WHERE fthg IS NOT NULL AND ftag IS NOT NULL")
            matches_db = cursor.fetchall()
            for m_league, m_date, m_home, m_away, m_fthg, m_ftag in matches_db:
                m_date_str = str(m_date)[:10]
                m_home_l = str(m_home).lower()
                m_away_l = str(m_away).lower()

                for p in pendientes:
                    p_id, p_liga, p_loc, p_vis, p_loc_csv, p_vis_csv, p_fecha, p_pred = p
                    if p_fecha == m_date_str:
                        loc_match = (p_loc or '').lower() == m_home_l or (p_loc_csv or '').lower() == m_home_l
                        vis_match = (p_vis or '').lower() == m_away_l or (p_vis_csv or '').lower() == m_away_l
                        if loc_match and vis_match:
                            res_real = determinar_resultado_real(int(m_fthg), int(m_ftag))
                            acierto = 1 if validar_acierto(p_pred, res_real) else 0
                            cursor.execute(
                                """UPDATE predictions_audit SET
                                   resultado_real = ?, goles_local = ?, goles_visitante = ?,
                                   resultado_registrado_at = ?, acierto_1x2 = ?
                                   WHERE match_id = ? AND resultado_real IS NULL""",
                                (res_real, int(m_fthg), int(m_ftag), datetime.now(timezone.utc).isoformat() + 'Z', acierto, p_id)
                            )
                            actualizados += cursor.rowcount
    except Exception as e:
        logger.debug(f"Error sincronizando desde tabla matches: {e}")

    conn.commit()
    conn.close()
    return actualizados


def obtener_historial_audit(liga_id: int, days_back: int, auto_sync: bool = True) -> Tuple[List[Dict], Dict]:
    """
    Obtiene historial de predicciones auditadas desde la DB de football_data.
    """
    if auto_sync:
        try:
            sincronizar_resultados_audit(DB_PATH)
        except Exception as e:
            logger.debug(f"Auto-sync de resultados audit falló: {e}")

    conn = get_db_connection(DB_PATH, readonly=True)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT local, visitante, fecha_partido, prob_local, prob_empate, prob_visitante,
               prob_1x, prob_x2, prob_12, prediccion_1x2, resultado_real,
               goles_local, goles_visitante, acierto_1x2
        FROM predictions_audit
        WHERE liga_id = ?
          AND fecha_partido >= datetime('now', ? || ' days')
          AND resultado_real IS NOT NULL
        ORDER BY fecha_partido DESC
        """,
        (liga_id, f'-{days_back}')
    )

    rows = cursor.fetchall()
    conn.close()

    resultados = []
    aciertos = 0
    fallos = 0
    sin_prediccion = 0

    for row in rows:
        (local, visitante, fecha_partido, prob_local, prob_empate, prob_visitante,
         prob_1x, prob_x2, prob_12, prediccion_1x2, resultado_real,
         goles_local, goles_visitante, acierto_1x2) = row

        if prediccion_1x2 == 'HOME_WIN':
            prediccion_texto = 'Local'
            prediccion_prob = round((prob_local or 0) * 100, 1)
        elif prediccion_1x2 == 'AWAY_WIN':
            prediccion_texto = 'Visitante'
            prediccion_prob = round((prob_visitante or 0) * 100, 1)
        elif prediccion_1x2 == 'DRAW':
            prediccion_texto = 'Empate'
            prediccion_prob = round((prob_empate or 0) * 100, 1)
        elif prediccion_1x2 == '1X':
            prediccion_texto = '1X'
            prediccion_prob = round((prob_1x or 0) * 100, 1)
        elif prediccion_1x2 == 'X2':
            prediccion_texto = 'X2'
            prediccion_prob = round((prob_x2 or 0) * 100, 1)
        elif prediccion_1x2 == '12':
            prediccion_texto = '12'
            prediccion_prob = round((prob_12 or 0) * 100, 1)
        else:
            prediccion_texto = prediccion_1x2 or ''
            prediccion_prob = 0

        acierto = None
        if acierto_1x2 is not None:
            acierto = bool(acierto_1x2)
            if acierto:
                aciertos += 1
            else:
                fallos += 1
        else:
            sin_prediccion += 1

        resultados.append({
            'local': local,
            'visitante': visitante,
            'goles_local': goles_local,
            'goles_visitante': goles_visitante,
            'resultado_real': resultado_real,
            'prediccion_ia': prediccion_1x2,
            'prediccion_texto': prediccion_texto,
            'prediccion_prob': prediccion_prob,
            'prob_local': round((prob_local or 0) * 100, 1),
            'prob_empate': round((prob_empate or 0) * 100, 1),
            'prob_visitante': round((prob_visitante or 0) * 100, 1),
            'acierto': acierto,
            'fecha': (fecha_partido or '')[:10],
            'error': None
        })

    total = len(resultados)
    evaluados = aciertos + fallos
    precision = round((aciertos / evaluados * 100), 1) if evaluados > 0 else 0

    estadisticas = {
        'total_partidos': total,
        'evaluados': evaluados,
        'aciertos': aciertos,
        'fallos': fallos,
        'sin_prediccion': sin_prediccion,
        'precision': precision
    }

    return resultados, estadisticas

