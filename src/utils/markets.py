"""
Centralized Betting Markets and Recommendations
================================================
Módulo centralizado para la lógica de apuestas, mercados derivados,
recomendaciones y semáforos de confianza.

Autor: Timba Team
"""

from typing import Dict, List, Optional
from scipy.stats import poisson

# ========== UMBRALES GLOBALES DE CONFIANZA ==========
PREDICCION_UMBRAL_GANA = 0.55
PREDICCION_UMBRAL_DOBLE = 0.70
UMBRAL_ALTO = 0.70
UMBRAL_MEDIO = 0.55


def obtener_mejor_recomendacion(prediccion: Dict) -> str:
    """
    Retorna la mejor recomendación corta para mostrar en tarjetas y tablas de fixtures.
    
    Args:
        prediccion: Diccionario con probabilidades del partido
        
    Returns:
        String con recomendación (ej: "1 (65%)", "1X", "Over 2.5", "—")
    """
    if not prediccion:
        return "—"
        
    prob_local = prediccion.get('Prob_Local', 0.0)
    prob_vis = prediccion.get('Prob_Vis', 0.0)
    
    if prob_local >= PREDICCION_UMBRAL_GANA:
        return f"1 ({round(prob_local * 100)}%)"
    elif prob_vis >= PREDICCION_UMBRAL_GANA:
        return f"2 ({round(prob_vis * 100)}%)"
    elif prediccion.get('Prob_1X', 0.0) >= PREDICCION_UMBRAL_DOBLE:
        return "1X"
    elif prediccion.get('Prob_X2', 0.0) >= PREDICCION_UMBRAL_DOBLE:
        return "X2"
    elif prediccion.get('Over_25', 0.0) >= 0.65:
        return "Over 2.5"
    elif prediccion.get('Over_15', 0.0) >= 0.75:
        return "Over 1.5"
    else:
        return "—"


def determinar_prediccion_1x2(
    prediccion: Dict,
    umbral_gana: float = PREDICCION_UMBRAL_GANA,
    umbral_doble: float = PREDICCION_UMBRAL_DOBLE
) -> str:
    """
    Determina el código de predicción 1X2 formal para auditoría y evaluación de aciertos.
    
    Args:
        prediccion: Diccionario con probabilidades
        umbral_gana: Umbral mínimo para victoria directa (default: 0.55)
        umbral_doble: Umbral mínimo para doble oportunidad (default: 0.70)
        
    Returns:
        Código estándar: 'HOME_WIN', 'AWAY_WIN', '1X', 'X2', '12', 'DRAW'
    """
    if not prediccion:
        return 'DRAW'
        
    prob_local = prediccion.get('Prob_Local', 0.0)
    prob_empate = prediccion.get('Prob_Empate', 0.0)
    prob_vis = prediccion.get('Prob_Vis', 0.0)

    if prob_local >= umbral_gana:
        return 'HOME_WIN'
    if prob_vis >= umbral_gana:
        return 'AWAY_WIN'

    if prediccion.get('Prob_1X', 0.0) >= umbral_doble:
        return '1X'
    if prediccion.get('Prob_X2', 0.0) >= umbral_doble:
        return 'X2'
    if prediccion.get('Prob_12', 0.0) >= umbral_doble:
        return '12'

    # Fallback: la opción 1X2 individual más probable
    valores = {
        'HOME_WIN': prob_local,
        'DRAW': prob_empate,
        'AWAY_WIN': prob_vis
    }
    return max(valores, key=valores.get)


def generar_recomendaciones(
    prediccion: Dict,
    umbral_alto: float = UMBRAL_ALTO,
    umbral_medio: float = UMBRAL_MEDIO
) -> List[Dict]:
    """
    Genera lista detallada de recomendaciones basadas en probabilidades (Semáforo).
    Incluye mercados de Goles, Córners, Tarjetas y Tarjeta Roja.
    
    Returns:
        Lista de dicts ordenada por probabilidad descendente
    """
    if not prediccion:
        return []
        
    recos = []
    
    # Reglas de Goles
    reglas_goles = [
        ('Prob_1X', 'Doble Oportunidad: Local o Empate', '1X', '⚽'),
        ('Prob_X2', 'Doble Oportunidad: Empate o Visitante', 'X2', '⚽'),
        ('Prob_12', 'Sin Empate: Gana alguien', '12', '⚽'),
        ('Over_15', 'Más de 1.5 Goles', 'Over 1.5 Goles', '⚽'),
        ('Over_25', 'Más de 2.5 Goles', 'Over 2.5 Goles', '⚽'),
        ('Under_35', 'Menos de 3.5 Goles (Seguridad)', 'Under 3.5 Goles', '⚽'),
    ]
    
    # Reglas de Córners
    reglas_corners = [
        ('Over_85', 'Más de 8.5 Córners', 'Over 8.5 Córners', '🚩'),
        ('Over_95', 'Más de 9.5 Córners', 'Over 9.5 Córners', '🚩'),
        ('Prob_Local_Mas_Corners', 'Local saca más córners', 'Local +Córners', '🚩'),
    ]
    
    # Reglas de Tarjetas
    reglas_tarjetas = [
        ('Over_25_Cards', 'Más de 2.5 Tarjetas Amarillas', 'Over 2.5 Tarjetas', '🟨'),
        ('Over_35_Cards', 'Más de 3.5 Tarjetas Amarillas', 'Over 3.5 Tarjetas', '🟨'),
        ('Over_45_Cards', 'Más de 4.5 Tarjetas Amarillas', 'Over 4.5 Tarjetas', '🟨'),
        ('Under_55_Cards', 'Menos de 5.5 Tarjetas (Seguro)', 'Under 5.5 Tarjetas', '🟨'),
    ]
    
    todas_reglas = reglas_goles + reglas_corners + reglas_tarjetas
    
    for key, texto, corto, emoji in todas_reglas:
        prob = prediccion.get(key, 0.0)
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
    
    # Regla Especial: Tarjeta Roja (umbral más bajo porque eventos son infrecuentes)
    prob_roja = prediccion.get('Prob_Red_Card', 0.0)
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
    
    recos.sort(key=lambda x: x['prob'], reverse=True)
    return recos


def calcular_semaforo(
    probabilidad: float,
    umbral_alto: float = UMBRAL_ALTO,
    umbral_medio: float = UMBRAL_MEDIO
) -> Dict:
    """
    Calcula nivel de semáforo visual para UI y badges.
    """
    if probabilidad >= umbral_alto:
        return {
            'nivel': 'ALTO',
            'badge_class': 'success',
            'color': '#28a745',
            'icono': '🟢'
        }
    elif probabilidad >= umbral_medio:
        return {
            'nivel': 'MEDIO',
            'badge_class': 'warning',
            'color': '#ffc107',
            'icono': '🟡'
        }
    else:
        return {
            'nivel': 'BAJO',
            'badge_class': 'secondary',
            'color': '#6c757d',
            'icono': '🔴'
        }


def calcular_mercados_adicionales(
    lambda_local: float,
    lambda_vis: float,
    f_local: Dict,
    f_vis: Dict
) -> Dict:
    """
    Calcula todos los mercados adicionales (córners, tarjetas, doble oportunidad, over/under).
    """
    lambda_total = lambda_local + lambda_vis
    
    over_15 = float(1.0 - poisson.cdf(1, lambda_total))
    over_25 = float(1.0 - poisson.cdf(2, lambda_total))
    under_35 = float(poisson.cdf(3, lambda_total))
    
    # Córners
    corners_lambda_local = float(f_local.get('Corners_Casa', 0.0) or 0.0)
    corners_lambda_vis = float(f_vis.get('Corners_Fuera', 0.0) or 0.0)
    corners_lambda_total = corners_lambda_local + corners_lambda_vis
    
    over_85 = float(1.0 - poisson.cdf(8, corners_lambda_total)) if corners_lambda_total > 0 else 0.5
    over_95 = float(1.0 - poisson.cdf(9, corners_lambda_total)) if corners_lambda_total > 0 else 0.5
    under_105 = float(poisson.cdf(10, corners_lambda_total)) if corners_lambda_total > 0 else 0.5
    
    if corners_lambda_local > 0 and corners_lambda_vis > 0:
        ratio_corners = corners_lambda_local / corners_lambda_vis
        if ratio_corners > 1.2:
            prob_local_mas_corners, prob_empate_corners, prob_vis_mas_corners = 0.65, 0.25, 0.10
        elif ratio_corners < 0.83:
            prob_local_mas_corners, prob_empate_corners, prob_vis_mas_corners = 0.10, 0.25, 0.65
        else:
            prob_local_mas_corners, prob_empate_corners, prob_vis_mas_corners = 0.35, 0.40, 0.25
    else:
        prob_local_mas_corners, prob_empate_corners, prob_vis_mas_corners = 0.33, 0.34, 0.33
        
    # Tarjetas
    tarjetas_am_local = float(f_local.get('Tarjetas_Am_Promedio', 0.0) or 0.0)
    tarjetas_am_vis = float(f_vis.get('Tarjetas_Am_Promedio', 0.0) or 0.0)
    tarjetas_am_total = tarjetas_am_local + tarjetas_am_vis
    
    tarjetas_ro_local = float(f_local.get('Tarjetas_Ro_Promedio', 0.0) or 0.0)
    tarjetas_ro_vis = float(f_vis.get('Tarjetas_Ro_Promedio', 0.0) or 0.0)
    tarjetas_ro_total = tarjetas_ro_local + tarjetas_ro_vis
    
    if tarjetas_am_total > 0:
        over_25_cards = float(1.0 - poisson.cdf(2, tarjetas_am_total))
        over_35_cards = float(1.0 - poisson.cdf(3, tarjetas_am_total))
        over_45_cards = float(1.0 - poisson.cdf(4, tarjetas_am_total))
        under_55_cards = float(poisson.cdf(5, tarjetas_am_total))
    else:
        over_25_cards = over_35_cards = over_45_cards = under_55_cards = 0.5
        
    if tarjetas_ro_total > 0:
        prob_red_card = float(1.0 - poisson.pmf(0, tarjetas_ro_total))
    else:
        prob_red_card = 0.05
        
    if tarjetas_am_local > 0 and tarjetas_am_vis > 0:
        ratio_cards = tarjetas_am_local / tarjetas_am_vis
        if ratio_cards > 1.3:
            prob_local_mas_cards, prob_vis_mas_cards = 0.60, 0.25
        elif ratio_cards < 0.77:
            prob_local_mas_cards, prob_vis_mas_cards = 0.25, 0.60
        else:
            prob_local_mas_cards, prob_vis_mas_cards = 0.40, 0.40
    else:
        prob_local_mas_cards, prob_vis_mas_cards = 0.45, 0.45
        
    return {
        'Over_15': over_15,
        'Over_25': over_25,
        'Under_35': under_35,
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
