"""
Unit tests for Centralized Betting Markets & Recommendations
============================================================
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from utils.markets import (
    obtener_mejor_recomendacion,
    determinar_prediccion_1x2,
    generar_recomendaciones,
    calcular_semaforo,
    calcular_mercados_adicionales,
)


def test_determinar_prediccion_1x2_rules():
    # Strong home win
    pred_home = {'Prob_Local': 0.65, 'Prob_Empate': 0.20, 'Prob_Vis': 0.15, 'Prob_1X': 0.85, 'Prob_X2': 0.35, 'Prob_12': 0.80}
    assert determinar_prediccion_1x2(pred_home) == 'HOME_WIN'

    # Strong away win
    pred_away = {'Prob_Local': 0.15, 'Prob_Empate': 0.20, 'Prob_Vis': 0.65, 'Prob_1X': 0.35, 'Prob_X2': 0.85, 'Prob_12': 0.80}
    assert determinar_prediccion_1x2(pred_away) == 'AWAY_WIN'

    # Double chance 1X
    pred_1x = {'Prob_Local': 0.45, 'Prob_Empate': 0.35, 'Prob_Vis': 0.20, 'Prob_1X': 0.80, 'Prob_X2': 0.55, 'Prob_12': 0.65}
    assert determinar_prediccion_1x2(pred_1x) == '1X'

    # Double chance X2
    pred_x2 = {'Prob_Local': 0.20, 'Prob_Empate': 0.35, 'Prob_Vis': 0.45, 'Prob_1X': 0.55, 'Prob_X2': 0.80, 'Prob_12': 0.65}
    assert determinar_prediccion_1x2(pred_x2) == 'X2'


def test_obtener_mejor_recomendacion_string():
    pred_home = {'Prob_Local': 0.62, 'Prob_Empate': 0.20, 'Prob_Vis': 0.18}
    reco = obtener_mejor_recomendacion(pred_home)
    assert '1' in reco and '62%' in reco

    pred_over = {'Prob_Local': 0.40, 'Prob_Empate': 0.30, 'Prob_Vis': 0.30, 'Prob_1X': 0.70, 'Over_25': 0.68}
    reco_over = obtener_mejor_recomendacion(pred_over)
    assert reco_over in ['1X', 'Over 2.5']


def test_generar_recomendaciones_badges():
    pred = {
        'Prob_1X': 0.85,
        'Over_15': 0.80,
        'Over_25': 0.60,
        'Over_85': 0.72,
        'Over_25_Cards': 0.75,
        'Prob_Red_Card': 0.22,
    }
    
    recos = generar_recomendaciones(pred)
    assert len(recos) >= 4
    
    # Must be ordered by probability descending
    probs = [r['prob'] for r in recos]
    assert probs == sorted(probs, reverse=True)
    
    # Red card rule creates a danger badge
    red_recos = [r for r in recos if 'Roja' in r['texto']]
    assert len(red_recos) == 1
    assert red_recos[0]['class'] == 'danger'


def test_calcular_semaforo():
    assert calcular_semaforo(0.75)['nivel'] == 'ALTO'
    assert calcular_semaforo(0.60)['nivel'] == 'MEDIO'
    assert calcular_semaforo(0.40)['nivel'] == 'BAJO'


def test_value_betting_and_kelly():
    from utils.markets import calcular_valor_esperado, calcular_criterio_kelly, evaluar_value_bets
    
    # Probabilidad 50% con cuota 2.20 -> EV = 0.50 * 2.20 - 1 = +0.10 (10% EV)
    ev = calcular_valor_esperado(0.50, 2.20)
    assert round(ev, 2) == 0.10
    
    # Kelly: b = 1.20, p = 0.50, q = 0.50 -> f* = (1.20*0.50 - 0.50)/1.20 = 0.10/1.20 = 8.33%
    # Con fraccion 0.25 (cuarto de Kelly) -> 2.08% stake
    kelly = calcular_criterio_kelly(0.50, 2.20, fraccion=0.25)
    assert 2.0 <= kelly <= 2.2
    
    # Apuesta sin valor: prob 40% con cuota 2.00 -> EV = -0.20
    ev_neg = calcular_valor_esperado(0.40, 2.00)
    assert ev_neg < 0
    assert calcular_criterio_kelly(0.40, 2.00) == 0.0
    
    # Evaluar lista de apuestas de valor
    pred = {
        'Prob_Local': 0.55,
        'Prob_Empate': 0.25,
        'Prob_Vis': 0.20,
        'Over_25': 0.65
    }
    cuotas = {
        'B365H': 2.10,  # EV = 0.55 * 2.10 - 1 = +0.155 (15.5%) -> Value Bet
        'B365D': 3.20,  # EV = 0.25 * 3.20 - 1 = -0.20 -> No Value
        'B365A': 4.00,  # EV = 0.20 * 4.00 - 1 = -0.20 -> No Value
        'B365_O25': 1.80  # EV = 0.65 * 1.80 - 1 = +0.170 (17%) -> Value Bet
    }
    
    vb = evaluar_value_bets(pred, cuotas, min_ev=0.05)
    assert len(vb) == 2
    assert vb[0]['ev_pct'] > 0
    assert all('kelly_stake_pct' in bet for bet in vb)

