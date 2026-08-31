"""
Unit Tests for Timba Telegram Bot Module
========================================
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from bot.formatters import (
    format_progress_bar,
    format_welcome_message,
    format_leagues_list,
    format_prediction_card,
    format_live_prediction_card,
    format_live_matches_summary,
    format_upcoming_fixtures,
    format_value_bets_summary
)
from bot.handlers import parse_prediction_args, parse_inplay_args, filtrar_partidos_por_liga
from bot.bot_app import create_bot_application
from timba_core import LIGAS


def test_format_progress_bar():
    bar0 = format_progress_bar(0.0, width=10)
    assert bar0 == "░" * 10
    bar50 = format_progress_bar(50.0, width=10)
    assert bar50 == "█████░░░░░"
    bar100 = format_progress_bar(100.0, width=10)
    assert bar100 == "█" * 10


def test_format_welcome_message():
    msg = format_welcome_message()
    assert "Timba Predictor Bot" in msg
    assert "/live" in msg
    assert "/predecir" in msg
    assert "/inplay" in msg


def test_format_leagues_list():
    msg = format_leagues_list(LIGAS)
    assert "Premier League" in msg
    assert "La Liga" in msg
    assert "Champions League" in msg


def test_format_prediction_card_html_escape():
    mock_pred = {
        'Prob_Local': 0.55,
        'Prob_Empate': 0.25,
        'Prob_Vis': 0.20,
        'Prob_1X': 0.80,
        'Prob_X2': 0.45,
        'Prob_12': 0.75,
        'xG_Local': 1.85,
        'xG_Vis': 1.05,
        'Over_15': 0.75,
        'Over_25': 0.52,
        'Under_35': 0.70,
        'BTTS_Prob': 0.55,
        'Top_3_Marcadores': [{'marcador': '2-1', 'prob': 0.12}]
    }
    # Test special characters like & in team names (Brighton & Hove Albion)
    card = format_prediction_card("Brighton & Hove Albion", "Chelsea", mock_pred, "Premier League")
    assert "Brighton &amp; Hove Albion" in card
    assert "Chelsea" in card
    assert "55.0%" in card
    assert "25.0%" in card
    assert "1.85" in card


def test_format_live_prediction_card_html_escape():
    mock_live = {
        'is_live': True,
        'minuto': 65,
        'marcador_actual': '2-1',
        'goles_local': 2,
        'goles_vis': 1,
        'rojas_local': 0,
        'rojas_vis': 1,
        'tiempo_restante_pct': 27.8,
        'xG_restante_local': 0.45,
        'xG_restante_vis': 0.18,
        'xG_total_esperado': 3.63,
        'prob_local': 84.5,
        'prob_empate': 11.2,
        'prob_visitante': 4.3,
        'proximo_gol': {
            'local': 35.0,
            'visitante': 12.0,
            'sin_mas_goles': 53.0
        },
        'top_marcadores_finales': [{'marcador': '2-1', 'prob': 48.2}],
        'estado_tactico': '🏠 Arsenal & City lidera (+1)'
    }
    card = format_live_prediction_card("Arsenal & Fans", "Chelsea", mock_live)
    assert "PREDICCIÓN EN VIVO" in card
    assert "Arsenal &amp; Fans" in card
    assert "Arsenal &amp; City lidera" in card
    assert "65'" in card
    assert "84.5%" in card


def test_parse_prediction_args():
    res1 = parse_prediction_args("Arsenal vs Chelsea")
    assert res1 == ("Arsenal", "Chelsea", None)

    res2 = parse_prediction_args("Real Madrid - Barcelona")
    assert res2 == ("Real Madrid", "Barcelona", None)

    res3 = parse_prediction_args("1 Arsenal Chelsea")
    assert res3 == ("Arsenal", "Chelsea", 1)


def test_parse_inplay_args():
    res1 = parse_inplay_args("Barcelona vs Real Madrid 2-1 min 70 rojas 0-1")
    assert res1 is not None
    assert res1['local'] == "Barcelona"
    assert res1['visitante'] == "Real Madrid"
    assert res1['home_score'] == 2
    assert res1['away_score'] == 1
    assert res1['minute'] == 70
    assert res1['red_cards_home'] == 0
    assert res1['red_cards_away'] == 1

    res2 = parse_inplay_args("Liverpool vs Man City 0-0 80")
    assert res2 is not None
    assert res2['local'] == "Liverpool"
    assert res2['visitante'] == "Man City"
    assert res2['home_score'] == 0
    assert res2['away_score'] == 0
    assert res2['minute'] == 80


def test_filtrar_partidos_por_liga():
    partidos = [
        {'competition': {'code': 'PL'}, 'home': 'Arsenal', 'away': 'Chelsea'},
        {'competition': {'code': 'PD'}, 'home': 'Real Madrid', 'away': 'Barcelona'}
    ]
    pl_matches = filtrar_partidos_por_liga(partidos, 1)  # 1 = PL
    assert len(pl_matches) == 1
    assert pl_matches[0]['home'] == 'Arsenal'

    all_matches = filtrar_partidos_por_liga(partidos, None)
    assert len(all_matches) == 2


def test_create_bot_application_validation():
    with pytest.raises(ValueError):
        create_bot_application("")
    
    with pytest.raises(ValueError):
        create_bot_application("short")

    app = create_bot_application("123456789:ABCdefGhIJKlmNoPQRstuVWXyz1234567")
    assert app is not None
