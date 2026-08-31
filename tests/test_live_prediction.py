"""
Unit and Integration Tests for In-Play (Live) Dynamic Predictions
=================================================================
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.prediction import predecir_partido_en_vivo, predecir_partido
from services.fixtures_service import enriquecer_partidos_con_prediccion
from app import app


@pytest.fixture
def mock_fuerzas():
    return {
        'Arsenal': {
            'Ataque_Casa': 1.30, 'Defensa_Casa': 0.80,
            'Ataque_Fuera': 1.15, 'Defensa_Fuera': 0.85,
            'Goles_Favor_Reciente': 2.0, 'Goles_Contra_Reciente': 0.8,
            'Corners_Promedio': 6.0, 'Tarjetas_Am_Promedio': 1.5,
            'Tarjetas_Rojas_Total': 0, 'Tiros_Puerta_Promedio': 6.5,
            'BTTS_pct': 50.0, 'Over25_pct': 60.0, 'Goles_2T_Promedio': 1.2
        },
        'Chelsea': {
            'Ataque_Casa': 1.10, 'Defensa_Casa': 0.95,
            'Ataque_Fuera': 1.05, 'Defensa_Fuera': 1.05,
            'Goles_Favor_Reciente': 1.4, 'Goles_Contra_Reciente': 1.2,
            'Corners_Promedio': 5.0, 'Tarjetas_Am_Promedio': 2.0,
            'Tarjetas_Rojas_Total': 0, 'Tiros_Puerta_Promedio': 4.5,
            'BTTS_pct': 45.0, 'Over25_pct': 50.0, 'Goles_2T_Promedio': 1.0
        }
    }


def test_live_prediction_goal_lead_increases_win_probability(mock_fuerzas):
    # Minuto 0: 0-0
    pred_min0 = predecir_partido_en_vivo(
        'Arsenal', 'Chelsea', mock_fuerzas, 1.50, 1.20,
        home_score=0, away_score=0, minute=0
    )
    # Minuto 75: Arsenal 2 - 0 Chelsea
    pred_min75_lead = predecir_partido_en_vivo(
        'Arsenal', 'Chelsea', mock_fuerzas, 1.50, 1.20,
        home_score=2, away_score=0, minute=75
    )

    assert pred_min0['is_live'] is True
    assert pred_min75_lead['is_live'] is True
    # Al ir ganando 2-0 en el min 75, la prob de victoria local debe ser mucho mayor (> 85%)
    assert pred_min75_lead['prob_local'] > pred_min0['prob_local']
    assert pred_min75_lead['prob_local'] >= 85.0
    assert pred_min75_lead['xG_restante_local'] < pred_min0['xG_restante_local']


def test_live_prediction_red_card_penalty(mock_fuerzas):
    # Minuto 30, 0-0, 11 vs 11
    pred_normal = predecir_partido_en_vivo(
        'Arsenal', 'Chelsea', mock_fuerzas, 1.50, 1.20,
        home_score=0, away_score=0, minute=30,
        red_cards_home=0, red_cards_away=0
    )
    # Minuto 30, 0-0, Arsenal con 1 tarjeta roja (10 jugadores)
    pred_red_card = predecir_partido_en_vivo(
        'Arsenal', 'Chelsea', mock_fuerzas, 1.50, 1.20,
        home_score=0, away_score=0, minute=30,
        red_cards_home=1, red_cards_away=0
    )

    # Con roja, disminuye prob local y aumenta prob visitante
    assert pred_red_card['prob_local'] < pred_normal['prob_local']
    assert pred_red_card['prob_visitante'] > pred_normal['prob_visitante']
    assert pred_red_card['xG_restante_local'] < pred_normal['xG_restante_local']
    assert pred_red_card['xG_restante_vis'] > pred_normal['xG_restante_vis']
    assert "🟥" in pred_red_card['estado_tactico']


def test_live_prediction_late_draw_convergence(mock_fuerzas):
    # Minuto 88: 1-1
    pred_min88 = predecir_partido_en_vivo(
        'Arsenal', 'Chelsea', mock_fuerzas, 1.50, 1.20,
        home_score=1, away_score=1, minute=88
    )

    # A falta de 2 min empatados, la probabilidad de empate final debe ser muy alta (> 70%)
    assert pred_min88['prob_empate'] >= 70.0
    # La probabilidad de "sin más goles" debe dominar
    assert pred_min88['proximo_gol']['sin_mas_goles'] >= 75.0


def test_live_prediction_next_goal_sum(mock_fuerzas):
    pred = predecir_partido_en_vivo(
        'Arsenal', 'Chelsea', mock_fuerzas, 1.50, 1.20,
        home_score=1, away_score=0, minute=55
    )
    pg = pred['proximo_gol']
    total_pg = pg['local'] + pg['visitante'] + pg['sin_mas_goles']
    assert 98.0 <= total_pg <= 102.0  # Suma aproximada a 100% con redondeos


def test_api_predict_endpoint_with_live_params():
    app.config['TESTING'] = True
    with app.test_client() as client:
        res = client.get('/api/v1/predict?liga_id=1&local=Arsenal&visitante=Chelsea&live=true&home_score=2&away_score=1&minute=70&red_cards_home=0&red_cards_away=1')
        assert res.status_code == 200
        data = res.get_json()

        assert 'prediccion_prematch' in data
        assert 'prediccion_live' in data
        assert data['prediccion_live'] is not None
        assert data['prediccion_live']['minuto'] == 70
        assert data['prediccion_live']['marcador_actual'] == '2-1'
        assert data['prediccion_live']['rojas_vis'] == 1
        assert data['prediccion_live']['prob_local'] > 60.0
