"""
Core Prediction Algorithms
===========================
Cálculo vectorizado de fuerzas de equipos, modelo Poisson para resultados,
mercados derivados y predicciones de Champions League.
"""

import gc
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.stats import poisson

logger = logging.getLogger(__name__)

# Intentar importar módulo Cython optimizado
try:
    from src.timba_fast import predecir_partido_optimizado
    USE_CYTHON = True
except ImportError:
    USE_CYTHON = False

from utils.shared import (
    emparejar_equipo,
    CHAMPIONS_EQUIPO_LIGA,
)
from utils.markets import calcular_mercados_adicionales

CSV_A_LIGA_ID = {
    "E0": 1,    # Premier League
    "SP1": 2,   # La Liga
    "D1": 3,    # Bundesliga
    "I1": 4,    # Serie A
    "F1": 5,    # Ligue 1
    "P1": 6,    # Primeira Liga
    "N1": 7,    # Eredivisie
    "B1": 8,    # First Division A (Bélgica)
    "ARG": 10,  # Liga Profesional Argentina
}


def calcular_fuerzas(df: pd.DataFrame) -> Tuple[Dict, float, float]:
    """
    Calcula fuerzas ofensivas, defensivas y estadísticas avanzadas por equipo.
    OPTIMIZADO: Totalmente vectorizado con GroupBy y NumPy para máximo rendimiento.
    """
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, format='mixed', errors='coerce')
    df = df.sort_values('Date').reset_index(drop=True)
    
    promedio_goles_local_liga = float(df['FTHG'].mean()) if len(df) > 0 else 0.0
    promedio_goles_visitante_liga = float(df['FTAG'].mean()) if len(df) > 0 else 0.0
    
    # 1. Agrupaciones globales para Casa y Fuera
    home_grp = df.groupby('HomeTeam')
    away_grp = df.groupby('AwayTeam')
    
    home_gf = home_grp['FTHG'].mean()
    home_ga = home_grp['FTAG'].mean()
    away_gf = away_grp['FTAG'].mean()
    away_ga = away_grp['FTHG'].mean()
    
    # 2. Córners
    tiene_datos_corners = 'HC' in df.columns and 'AC' in df.columns
    if tiene_datos_corners:
        home_hc = home_grp['HC'].mean()
        home_ac = home_grp['AC'].mean()
        away_ac = away_grp['AC'].mean()
        away_hc = away_grp['HC'].mean()
    else:
        home_hc = home_ac = away_ac = away_hc = None
    
    # 3. Tarjetas
    has_hy = 'HY' in df.columns
    has_ay = 'AY' in df.columns
    has_hr = 'HR' in df.columns
    has_ar = 'AR' in df.columns
    home_hy = home_grp['HY'].mean() if has_hy else None
    away_ay = away_grp['AY'].mean() if has_ay else None
    home_hr = home_grp['HR'].mean() if has_hr else None
    away_ar = away_grp['AR'].mean() if has_ar else None
    
    # 4. Tiros a puerta
    has_hst = 'HST' in df.columns
    has_ast = 'AST' in df.columns
    home_hst = home_grp['HST'].mean() if has_hst else None
    away_ast = away_grp['AST'].mean() if has_ast else None
    
    # 5. Partidos recientes (últimos 5 globales por equipo)
    cols_home = {'Date': df['Date'], 'Team': df['HomeTeam'], 'GF': df['FTHG'], 'GC': df['FTAG']}
    cols_away = {'Date': df['Date'], 'Team': df['AwayTeam'], 'GF': df['FTAG'], 'GC': df['FTHG']}
    df_all_matches = pd.concat([pd.DataFrame(cols_home), pd.DataFrame(cols_away)], ignore_index=True)
    df_all_matches = df_all_matches.sort_values('Date').reset_index(drop=True)
    
    recent_5 = df_all_matches.groupby('Team').tail(5)
    rec_gf = recent_5.groupby('Team')['GF'].mean()
    rec_gc = recent_5.groupby('Team')['GC'].mean()
    
    # 6. BTTS y Over 2.5
    df['is_btts'] = (df['FTHG'] > 0) & (df['FTAG'] > 0)
    df['is_over25'] = (df['FTHG'] + df['FTAG']) > 2.5
    
    home_btts_sum = home_grp['is_btts'].sum()
    away_btts_sum = away_grp['is_btts'].sum()
    home_over25_sum = home_grp['is_over25'].sum()
    away_over25_sum = away_grp['is_over25'].sum()
    home_count = home_grp.size()
    away_count = away_grp.size()
    
    # 7. Goles en 2T
    has_hthg = 'HTHG' in df.columns
    has_htag = 'HTAG' in df.columns
    home_g2t_sum = (df['FTHG'] - df['HTHG']).groupby(df['HomeTeam']).sum() if has_hthg else None
    home_g2t_cnt = (df['FTHG'] - df['HTHG']).dropna().groupby(df['HomeTeam']).size() if has_hthg else None
    away_g2t_sum = (df['FTAG'] - df['HTAG']).groupby(df['AwayTeam']).sum() if has_htag else None
    away_g2t_cnt = (df['FTAG'] - df['HTAG']).dropna().groupby(df['AwayTeam']).size() if has_htag else None
    
    equipos = sorted(set(df['HomeTeam'].dropna()).union(set(df['AwayTeam'].dropna())))
    fuerzas = {}
    
    for equipo in equipos:
        gf_c_glob = float(home_gf.get(equipo, 0.0))
        gc_c_glob = float(home_ga.get(equipo, 0.0))
        gf_f_glob = float(away_gf.get(equipo, 0.0))
        gc_f_glob = float(away_ga.get(equipo, 0.0))
        
        atq_c_glob = gf_c_glob / promedio_goles_local_liga if promedio_goles_local_liga > 0 else 0.0
        def_c_glob = gc_c_glob / promedio_goles_visitante_liga if promedio_goles_visitante_liga > 0 else 0.0
        atq_f_glob = gf_f_glob / promedio_goles_visitante_liga if promedio_goles_visitante_liga > 0 else 0.0
        def_f_glob = gc_f_glob / promedio_goles_local_liga if promedio_goles_local_liga > 0 else 0.0
        
        gf_rec = float(rec_gf.get(equipo, 0.0))
        gc_rec = float(rec_gc.get(equipo, 0.0))
        atq_rec = gf_rec / promedio_goles_local_liga if promedio_goles_local_liga > 0 else 0.0
        def_rec = gc_rec / promedio_goles_visitante_liga if promedio_goles_visitante_liga > 0 else 0.0
        
        atq_c_final = (atq_rec * 0.6) + (atq_c_glob * 0.4)
        def_c_final = (def_rec * 0.6) + (def_c_glob * 0.4)
        atq_f_final = (atq_rec * 0.6) + (atq_f_glob * 0.4)
        def_f_final = (def_rec * 0.6) + (def_f_glob * 0.4)
        
        # Córners
        if tiene_datos_corners:
            c_c_glob = float(home_hc.get(equipo, 0.0))
            c_f_glob = float(away_ac.get(equipo, 0.0))
            c_c_contra = float(home_ac.get(equipo, 0.0))
            c_f_contra = float(away_hc.get(equipo, 0.0))
        else:
            c_c_glob = c_f_glob = c_c_contra = c_f_contra = 0.0
            
        c_c_rec = c_c_glob
        c_f_rec = c_f_glob
        corners_casa = (c_c_rec * 0.75) + (c_c_glob * 0.25)
        corners_fuera = (c_f_rec * 0.75) + (c_f_glob * 0.25)
        
        # Tarjetas
        tarjetas_am_casa = float(home_hy.get(equipo, 0.0)) if home_hy is not None else 0.0
        tarjetas_am_fuera = float(away_ay.get(equipo, 0.0)) if away_ay is not None else 0.0
        tarjetas_ro_casa = float(home_hr.get(equipo, 0.0)) if home_hr is not None else 0.0
        tarjetas_ro_fuera = float(away_ar.get(equipo, 0.0)) if away_ar is not None else 0.0
        
        # Eficiencia de tiro
        hst_c = float(home_hst.get(equipo, 0.0)) if home_hst is not None else 0.0
        ast_f = float(away_ast.get(equipo, 0.0)) if away_ast is not None else 0.0
        ef_c = (gf_c_glob / hst_c) * 100 if hst_c > 0 else 0.0
        ef_f = (gf_f_glob / ast_f) * 100 if ast_f > 0 else 0.0
        ef_prom = (ef_c + ef_f) / 2.0
        
        # BTTS y Over 2.5
        tot_pts = int(home_count.get(equipo, 0)) + int(away_count.get(equipo, 0))
        if tot_pts > 0:
            tot_btts = int(home_btts_sum.get(equipo, 0)) + int(away_btts_sum.get(equipo, 0))
            tot_o25 = int(home_over25_sum.get(equipo, 0)) + int(away_over25_sum.get(equipo, 0))
            btts_pct = (tot_btts / tot_pts) * 100.0
            over25_pct = (tot_o25 / tot_pts) * 100.0
        else:
            btts_pct = 0.0
            over25_pct = 0.0
            
        # Goles 2T
        g2t_tot = 0.0
        g2t_cnt = 0
        if home_g2t_sum is not None and equipo in home_g2t_sum:
            g2t_tot += float(home_g2t_sum.get(equipo, 0.0))
            g2t_cnt += int(home_g2t_cnt.get(equipo, 0))
        if away_g2t_sum is not None and equipo in away_g2t_sum:
            g2t_tot += float(away_g2t_sum.get(equipo, 0.0))
            g2t_cnt += int(away_g2t_cnt.get(equipo, 0))
        g2t_prom = (g2t_tot / g2t_cnt) if g2t_cnt > 0 else 0.0
        
        fuerzas[equipo] = {
            'Ataque_Casa': atq_c_final,
            'Defensa_Casa': def_c_final,
            'Ataque_Fuera': atq_f_final,
            'Defensa_Fuera': def_f_final,
            'Ataque_Casa_Global': atq_c_glob,
            'Defensa_Casa_Global': def_c_glob,
            'Ataque_Fuera_Global': atq_f_glob,
            'Defensa_Fuera_Global': def_f_glob,
            'Ataque_Reciente': atq_rec,
            'Defensa_Reciente': def_rec,
            'Goles_Favor_Reciente': gf_rec,
            'Goles_Contra_Reciente': gc_rec,
            'Corners_Casa': corners_casa,
            'Corners_Fuera': corners_fuera,
            'Corners_Casa_Contra': c_c_contra,
            'Corners_Fuera_Contra': c_f_contra,
            'Corners_Promedio': (corners_casa + corners_fuera) / 2.0,
            'Tarjetas_Am_Casa': tarjetas_am_casa,
            'Tarjetas_Am_Fuera': tarjetas_am_fuera,
            'Tarjetas_Am_Promedio': (tarjetas_am_casa + tarjetas_am_fuera) / 2.0,
            'Tarjetas_Ro_Casa': tarjetas_ro_casa,
            'Tarjetas_Ro_Fuera': tarjetas_ro_fuera,
            'Tarjetas_Ro_Promedio': (tarjetas_ro_casa + tarjetas_ro_fuera) / 2.0,
            'Eficiencia_Tiro_Casa_pct': ef_c,
            'Eficiencia_Tiro_Fuera_pct': ef_f,
            'Eficiencia_Tiro_Promedio_pct': ef_prom,
            'BTTS_pct': btts_pct,
            'Over25_pct': over25_pct,
            'Goles_2T_Promedio': g2t_prom,
        }
    
    gc.collect()
    return fuerzas, promedio_goles_local_liga, promedio_goles_visitante_liga


def aplicar_ajuste_dixon_coles(
    matriz_prob: np.ndarray,
    lambda_local: float,
    lambda_vis: float,
    rho: float = -0.11
) -> np.ndarray:
    """
    Ajuste de Dixon y Coles (1997) para modelar la correlación entre goles de local y visitante
    en marcadores de bajo puntaje (0-0, 1-0, 0-1, 1-1). Corrige la subdispersión de empates.
    """
    if matriz_prob.shape[0] < 2 or matriz_prob.shape[1] < 2 or rho == 0.0:
        return matriz_prob
        
    mat = matriz_prob.copy()
    
    tau_00 = max(0.0, 1.0 - (lambda_local * lambda_vis * rho))
    tau_01 = max(0.0, 1.0 + (lambda_local * rho))
    tau_10 = max(0.0, 1.0 + (lambda_vis * rho))
    tau_11 = max(0.0, 1.0 - rho)
    
    mat[0, 0] *= tau_00
    mat[0, 1] *= tau_01
    mat[1, 0] *= tau_10
    mat[1, 1] *= tau_11
    
    total = np.sum(mat)
    if total > 0:
        mat /= total
    return mat


# Coeficientes relativos de fuerza por liga para normalización inter-liga (Champions League)
COEFICIENTES_LIGAS = {
    'E0': 1.15,   # Premier League
    'SP1': 1.10,  # La Liga
    'D1': 1.05,   # Bundesliga
    'I1': 1.05,   # Serie A
    'F1': 0.95,   # Ligue 1
    'P1': 0.88,   # Primeira Liga
    'N1': 0.85,   # Eredivisie
    'B1': 0.82,   # Liga Belga
    'ARG': 0.85,  # Liga Argentina
}


def predecir_partido(
    local: str,
    visitante: str,
    fuerzas: Dict,
    media_liga_local: float,
    media_liga_visitante: float,
    aplicar_dixon_coles: bool = True
) -> Optional[Dict]:
    """
    Predice probabilidades 1X2, marcadores exactos y mercados derivados.
    Usa módulo Cython compilado con fallback vectorizado NumPy y ajuste Dixon-Coles.
    """
    if local not in fuerzas or visitante not in fuerzas:
        return None
    
    # Motor Cython
    if USE_CYTHON and not aplicar_dixon_coles:
        try:
            resultado = predecir_partido_optimizado(
                local, visitante, fuerzas, media_liga_local, media_liga_visitante
            )
            if resultado is not None:
                return resultado
        except Exception as e:
            logger.error(f"⚠️  Error en motor Cython: {e}. Usando fallback Python.")
    
    # Fallback NumPy vectorizado con ajuste Dixon-Coles
    f_loc = fuerzas[local]
    f_vis = fuerzas[visitante]
    
    fuerza_ataque_local = f_loc['Ataque_Casa']
    fuerza_defensa_visitante = f_vis['Defensa_Fuera']
    lambda_local = fuerza_ataque_local * fuerza_defensa_visitante * media_liga_local
    fuerza_ataque_visitante = f_vis['Ataque_Fuera']
    fuerza_defensa_local = f_loc['Defensa_Casa']
    lambda_visitante = fuerza_ataque_visitante * fuerza_defensa_local * media_liga_visitante
    
    max_goles = 10
    k = np.arange(max_goles + 1)
    prob_local_arr = poisson.pmf(k, lambda_local)
    prob_vis_arr = poisson.pmf(k, lambda_visitante)
    
    matriz_prob = np.outer(prob_local_arr, prob_vis_arr)
    
    if aplicar_dixon_coles:
        matriz_prob = aplicar_ajuste_dixon_coles(matriz_prob, lambda_local, lambda_visitante)
    
    empate = float(np.trace(matriz_prob))
    victoria_local = float(np.sum(np.tril(matriz_prob, -1)))
    victoria_visitante = float(np.sum(np.triu(matriz_prob, 1)))
    
    total_prob = victoria_local + empate + victoria_visitante
    if total_prob > 0:
        victoria_local /= total_prob
        empate /= total_prob
        victoria_visitante /= total_prob
    
    # Top 3 marcadores
    sub_mat = matriz_prob[:7, :7]
    indices_top = np.argsort(sub_mat.ravel())[::-1][:3]
    top_3_marcadores = [
        {'marcador': f'{idx // 7}-{idx % 7}', 'prob': float(sub_mat.ravel()[idx])}
        for idx in indices_top
    ]
    
    # Doble oportunidad
    prob_1x = victoria_local + empate
    prob_x2 = empate + victoria_visitante
    prob_12 = victoria_local + victoria_visitante
    
    # Mercados adicionales centralizados
    mercados = calcular_mercados_adicionales(lambda_local, lambda_visitante, f_loc, f_vis)
    
    resultado = {
        'xG_Local': lambda_local,
        'xG_Vis': lambda_visitante,
        'Goles_Esp_Local': lambda_local,
        'Goles_Esp_Vis': lambda_visitante,
        'Prob_Local': victoria_local,
        'Prob_Empate': empate,
        'Prob_Vis': victoria_visitante,
        'Goles_Favor_Local': f_loc['Goles_Favor_Reciente'],
        'Goles_Contra_Local': f_loc['Goles_Contra_Reciente'],
        'Goles_Favor_Vis': f_vis['Goles_Favor_Reciente'],
        'Goles_Contra_Vis': f_vis['Goles_Contra_Reciente'],
        'Corners_Local': f_loc['Corners_Promedio'],
        'Corners_Vis': f_vis['Corners_Promedio'],
        'Tarjetas_Am_Local': f_loc['Tarjetas_Am_Promedio'],
        'Tarjetas_Am_Vis': f_vis['Tarjetas_Am_Promedio'],
        'Tarjetas_Ro_Local': f_loc['Tarjetas_Ro_Promedio'],
        'Tarjetas_Ro_Vis': f_vis['Tarjetas_Ro_Promedio'],
        'Eficiencia_Tiro_Local_pct': f_loc.get('Eficiencia_Tiro_Promedio_pct', 0),
        'Eficiencia_Tiro_Vis_pct': f_vis.get('Eficiencia_Tiro_Promedio_pct', 0),
        'BTTS_Local_pct': f_loc.get('BTTS_pct', 0),
        'BTTS_Vis_pct': f_vis.get('BTTS_pct', 0),
        'Over25_Local_pct': f_loc.get('Over25_pct', 0),
        'Over25_Vis_pct': f_vis.get('Over25_pct', 0),
        'Goles_2T_Local': f_loc.get('Goles_2T_Promedio', 0),
        'Goles_2T_Vis': f_vis.get('Goles_2T_Promedio', 0),
        'Top_3_Marcadores': top_3_marcadores,
        'Prob_1X': prob_1x,
        'Prob_X2': prob_x2,
        'Prob_12': prob_12,
    }
    resultado.update(mercados)
    return resultado


def predecir_partido_champions(local: str, visitante: str, cache_fuerzas: dict) -> Optional[Dict]:
    """
    Predice un partido de UEFA Champions League combinando fuerzas de distintas ligas
    y aplicando ponderación de coeficientes inter-liga.
    """
    key_local = emparejar_equipo(local, list(CHAMPIONS_EQUIPO_LIGA.keys()))
    key_vis = emparejar_equipo(visitante, list(CHAMPIONS_EQUIPO_LIGA.keys()))

    liga_local_csv = CHAMPIONS_EQUIPO_LIGA.get(key_local)
    liga_vis_csv = CHAMPIONS_EQUIPO_LIGA.get(key_vis)

    if not liga_local_csv or not liga_vis_csv:
        logger.warning(f"No se encontró liga doméstica para: {local} ({key_local}->{liga_local_csv}), {visitante} ({key_vis}->{liga_vis_csv})")
        return None

    liga_local_id = CSV_A_LIGA_ID.get(liga_local_csv)
    liga_vis_id = CSV_A_LIGA_ID.get(liga_vis_csv)

    if liga_local_id is None or liga_vis_id is None:
        logger.warning(f"No se encontró liga_id para códigos CSV: {liga_local_csv}, {liga_vis_csv}")
        return None

    cache_local = cache_fuerzas.get(liga_local_id)
    cache_vis = cache_fuerzas.get(liga_vis_id)

    if not cache_local or not cache_vis:
        logger.warning(f"Cache de fuerzas incompleta para Champions: {liga_local_id}, {liga_vis_id}")
        return None

    fuerzas_local, media_local_local, media_vis_local, equipos_local = cache_local
    fuerzas_vis, media_local_vis, media_vis_vis, equipos_vis = cache_vis

    local_match = emparejar_equipo(local, equipos_local)
    visitante_match = emparejar_equipo(visitante, equipos_vis)

    if local_match not in fuerzas_local or visitante_match not in fuerzas_vis:
        logger.warning(f"Equipo no encontrado en cache de fuerzas: {local_match} o {visitante_match}")
        return None

    media_goles_local = (media_local_local + media_local_vis) / 2
    media_goles_vis = (media_vis_local + media_vis_vis) / 2

    # Ajuste por coeficiente de liga (calibración inter-liga)
    coef_local = COEFICIENTES_LIGAS.get(liga_local_csv, 1.0)
    coef_vis = COEFICIENTES_LIGAS.get(liga_vis_csv, 1.0)

    f_loc_ajustada = dict(fuerzas_local[local_match])
    f_vis_ajustada = dict(fuerzas_vis[visitante_match])

    f_loc_ajustada['Ataque_Casa'] = f_loc_ajustada.get('Ataque_Casa', 1.0) * coef_local
    f_loc_ajustada['Defensa_Casa'] = f_loc_ajustada.get('Defensa_Casa', 1.0) / coef_local if coef_local > 0 else 1.0

    f_vis_ajustada['Ataque_Fuera'] = f_vis_ajustada.get('Ataque_Fuera', 1.0) * coef_vis
    f_vis_ajustada['Defensa_Fuera'] = f_vis_ajustada.get('Defensa_Fuera', 1.0) / coef_vis if coef_vis > 0 else 1.0

    fuerzas_combinadas = {
        local_match: f_loc_ajustada,
        visitante_match: f_vis_ajustada,
    }

    return predecir_partido(local_match, visitante_match, fuerzas_combinadas, media_goles_local, media_goles_vis)


def obtener_h2h(local: str, visitante: str, df: pd.DataFrame) -> List[Dict]:
    """
    Obtiene el historial de enfrentamientos directos entre dos equipos.
    """
    if df is None or df.empty:
        return []
    h2h = []
    partidos_1 = df[(df['HomeTeam'] == local) & (df['AwayTeam'] == visitante)]
    for _, fila in partidos_1.iterrows():
        try:
            fecha = fila['Date']
            goles_l = int(fila['FTHG'])
            goles_v = int(fila['FTAG'])
            h2h.append({'Fecha': fecha, 'Local': local, 'Visitante': visitante, 'Goles_Local': goles_l, 'Goles_Visitante': goles_v})
        except (ValueError, KeyError) as e:
            logger.debug(f"Error parseando H2H (local): {e}")
            
    partidos_2 = df[(df['HomeTeam'] == visitante) & (df['AwayTeam'] == local)]
    for _, fila in partidos_2.iterrows():
        try:
            fecha = fila['Date']
            goles_l = int(fila['FTAG'])
            goles_v = int(fila['FTHG'])
            h2h.append({'Fecha': fecha, 'Local': local, 'Visitante': visitante, 'Goles_Local': goles_l, 'Goles_Visitante': goles_v})
        except (ValueError, KeyError) as e:
            logger.debug(f"Error parseando H2H (visitante): {e}")
            
    try:
        h2h.sort(key=lambda x: pd.to_datetime(x['Fecha'], dayfirst=True, format='mixed', errors='coerce'), reverse=True)
    except Exception as e:
        logger.warning(f"Error ordenando H2H por fecha: {e}")
        
    return h2h
