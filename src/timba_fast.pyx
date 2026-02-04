# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True
import cython
from libc.math cimport exp, pow, tgamma, ceil

# --- FUNCIONES C PURAS (Ultra rápidas) ---

cdef double c_poisson_pmf(int k, double lam):
    """Función de Masa de Probabilidad de Poisson en C"""
    if lam == 0:
        return 1.0 if k == 0 else 0.0
    return (pow(lam, k) * exp(-lam)) / tgamma(k + 1)

cdef double c_poisson_cdf(int k, double lam):
    """Función de Distribución Acumulada de Poisson en C"""
    cdef double sum_prob = 0.0
    cdef int i
    for i in range(k + 1):
        sum_prob += c_poisson_pmf(i, lam)
    return sum_prob

# --- FUNCIÓN PÚBLICA PARA PYTHON ---

def predecir_partido_optimizado(str local, str visitante, dict fuerzas, double media_liga_local, double media_liga_visitante):
    cdef double fuerza_ataque_local, fuerza_defensa_visitante, lambda_local
    cdef double fuerza_ataque_visitante, fuerza_defensa_local, lambda_visitante
    cdef int max_goles = 10
    cdef int goles_l, goles_v
    cdef double prob
    cdef double victoria_local = 0.0, empate = 0.0, victoria_visitante = 0.0
    cdef list marcadores_exactos = []
    
    if local not in fuerzas or visitante not in fuerzas:
        return None

    f_local = fuerzas[local]
    f_visita = fuerzas[visitante]
    
    fuerza_ataque_local = f_local['Ataque_Casa']
    fuerza_defensa_visitante = f_visita['Defensa_Fuera']
    lambda_local = fuerza_ataque_local * fuerza_defensa_visitante * media_liga_local

    fuerza_ataque_visitante = f_visita['Ataque_Fuera']
    fuerza_defensa_local = f_local['Defensa_Casa']
    lambda_visitante = fuerza_ataque_visitante * fuerza_defensa_local * media_liga_visitante

    cdef double prob_local_arr[11]
    cdef double prob_visitante_arr[11]
    
    for i in range(max_goles + 1):
        prob_local_arr[i] = c_poisson_pmf(i, lambda_local)
        prob_visitante_arr[i] = c_poisson_pmf(i, lambda_visitante)

    for goles_l in range(max_goles + 1):
        for goles_v in range(max_goles + 1):
            prob = prob_local_arr[goles_l] * prob_visitante_arr[goles_v]
            if goles_l > goles_v:
                victoria_local += prob
            elif goles_l == goles_v:
                empate += prob
            else:
                victoria_visitante += prob
            if goles_l <= 6 and goles_v <= 6:
                marcadores_exactos.append({'marcador': f'{goles_l}-{goles_v}', 'prob': prob})

    cdef double total_prob = victoria_local + empate + victoria_visitante
    if total_prob > 0:
        victoria_local /= total_prob
        empate /= total_prob
        victoria_visitante /= total_prob

    marcadores_exactos.sort(key=lambda x: x['prob'], reverse=True)
    
    # --- MERCADOS DE GOLES ---
    cdef double lambda_total = lambda_local + lambda_visitante
    cdef double over_15 = 1.0 - c_poisson_cdf(1, lambda_total)
    cdef double over_25 = 1.0 - c_poisson_cdf(2, lambda_total)
    cdef double under_35 = c_poisson_cdf(3, lambda_total)

    # --- MERCADOS DE CÓRNERS ---
    cdef double corners_lambda_local = f_local['Corners_Casa']
    cdef double corners_lambda_vis = f_visita['Corners_Fuera']
    cdef double corners_lambda_total = corners_lambda_local + corners_lambda_vis
    
    cdef double over_85 = 1.0 - c_poisson_cdf(8, corners_lambda_total)
    cdef double over_95 = 1.0 - c_poisson_cdf(9, corners_lambda_total)
    cdef double under_105 = c_poisson_cdf(10, corners_lambda_total)

    # Ganador Córners
    cdef double prob_local_mas_corners = 0.33
    cdef double prob_empate_corners = 0.34
    cdef double prob_vis_mas_corners = 0.33
    cdef double ratio_corners
    if corners_lambda_local > 0 and corners_lambda_vis > 0:
        ratio_corners = corners_lambda_local / corners_lambda_vis
        if ratio_corners > 1.2:
            prob_local_mas_corners = 0.65
            prob_empate_corners = 0.25
            prob_vis_mas_corners = 0.10
        elif ratio_corners < 0.83:
            prob_local_mas_corners = 0.10
            prob_empate_corners = 0.25
            prob_vis_mas_corners = 0.65
        else:
            prob_local_mas_corners = 0.35
            prob_empate_corners = 0.40
            prob_vis_mas_corners = 0.25

    # --- MERCADOS DE TARJETAS ---
    cdef double tarjetas_am_local = f_local['Tarjetas_Am_Promedio']
    cdef double tarjetas_am_vis = f_visita['Tarjetas_Am_Promedio']
    cdef double tarjetas_am_total = tarjetas_am_local + tarjetas_am_vis
    cdef double tarjetas_ro_total = f_local['Tarjetas_Ro_Promedio'] + f_visita['Tarjetas_Ro_Promedio']

    cdef double over_25_cards = 0.5
    cdef double over_35_cards = 0.5
    cdef double over_45_cards = 0.5
    cdef double under_55_cards = 0.5
    
    if tarjetas_am_total > 0:
        over_25_cards = 1.0 - c_poisson_cdf(2, tarjetas_am_total)
        over_35_cards = 1.0 - c_poisson_cdf(3, tarjetas_am_total)
        over_45_cards = 1.0 - c_poisson_cdf(4, tarjetas_am_total)
        under_55_cards = c_poisson_cdf(5, tarjetas_am_total)
        
    cdef double prob_red_card = 0.05
    if tarjetas_ro_total > 0:
        prob_red_card = 1.0 - c_poisson_cdf(0, tarjetas_ro_total) # Prob >= 1

    # Ganador Tarjetas
    cdef double prob_local_mas_cards = 0.45
    cdef double prob_vis_mas_cards = 0.45
    cdef double ratio_cards
    if tarjetas_am_local > 0 and tarjetas_am_vis > 0:
        ratio_cards = tarjetas_am_local / tarjetas_am_vis
        if ratio_cards > 1.3:
            prob_local_mas_cards = 0.60
            prob_vis_mas_cards = 0.25
        elif ratio_cards < 0.77:
            prob_local_mas_cards = 0.25
            prob_vis_mas_cards = 0.60
        else:
            prob_local_mas_cards = 0.40
            prob_vis_mas_cards = 0.40

    # RETORNO DEL DICCIONARIO COMPLETO
    return {
        'Goles_Esp_Local': lambda_local,
        'Goles_Esp_Vis': lambda_visitante,
        'Prob_Local': victoria_local,
        'Prob_Empate': empate,
        'Prob_Vis': victoria_visitante,
        'Goles_Favor_Local': f_local['Goles_Favor_Reciente'],
        'Goles_Contra_Local': f_local['Goles_Contra_Reciente'],
        'Goles_Favor_Vis': f_visita['Goles_Favor_Reciente'],
        'Goles_Contra_Vis': f_visita['Goles_Contra_Reciente'],
        'Corners_Local': f_local['Corners_Promedio'],
        'Corners_Vis': f_visita['Corners_Promedio'],
        'Tarjetas_Am_Local': tarjetas_am_local,
        'Tarjetas_Am_Vis': tarjetas_am_vis,
        'Tarjetas_Ro_Local': f_local['Tarjetas_Ro_Promedio'],
        'Tarjetas_Ro_Vis': f_visita['Tarjetas_Ro_Promedio'],
        'Eficiencia_Tiro_Local_pct': f_local.get('Eficiencia_Tiro_Promedio_pct', 0),
        'Eficiencia_Tiro_Vis_pct': f_visita.get('Eficiencia_Tiro_Promedio_pct', 0),
        'BTTS_Local_pct': f_local.get('BTTS_pct', 0),
        'BTTS_Vis_pct': f_visita.get('BTTS_pct', 0),
        'Over25_Local_pct': f_local.get('Over25_pct', 0),
        'Over25_Vis_pct': f_visita.get('Over25_pct', 0),
        'Goles_2T_Local': f_local.get('Goles_2T_Promedio', 0),
        'Goles_2T_Vis': f_visita.get('Goles_2T_Promedio', 0),
        'Top_3_Marcadores': marcadores_exactos[:3],
        'Over_15': over_15,
        'Over_25': over_25,
        'Under_35': under_35,
        'Prob_1X': victoria_local + empate,
        'Prob_X2': empate + victoria_visitante,
        'Prob_12': victoria_local + victoria_visitante,
        'Corners_Lambda_Total': corners_lambda_total,
        'Over_85': over_85,
        'Over_95': over_95,
        'Under_105': under_105,
        'Prob_Local_Mas_Corners': prob_local_mas_corners,
        'Prob_Empate_Corners': prob_empate_corners,
        'Prob_Vis_Mas_Corners': prob_vis_mas_corners,
        'Tarjetas_Am_Total': tarjetas_am_total,
        'Tarjetas_Ro_Total': tarjetas_ro_total,
        'Over_25_Cards': over_25_cards,
        'Over_35_Cards': over_35_cards,
        'Over_45_Cards': over_45_cards,
        'Under_55_Cards': under_55_cards,
        'Prob_Red_Card': prob_red_card,
        'Prob_Local_Mas_Cards': prob_local_mas_cards,
        'Prob_Vis_Mas_Cards': prob_vis_mas_cards,
    }