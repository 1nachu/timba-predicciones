"""
Unit tests for Vectorized Prediction & Mathematical Accuracy
============================================================
"""

import pytest
import numpy as np
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from core.prediction import calcular_fuerzas, predecir_partido, predecir_partido_champions, obtener_h2h
from db_data_provider import DatabaseDataProvider


@pytest.fixture
def sample_match_data():
    provider = DatabaseDataProvider()
    df = provider.get_data_from_db('E0', temporadas=1)
    if df is None or df.empty:
        # Fallback synthetic dataset
        df = pd.DataFrame({
            'Date': ['2025-08-15', '2025-08-16', '2025-08-22', '2025-08-23'],
            'HomeTeam': ['Arsenal', 'Chelsea', 'Arsenal', 'Liverpool'],
            'AwayTeam': ['Chelsea', 'Liverpool', 'Liverpool', 'Arsenal'],
            'FTHG': [2, 1, 3, 0],
            'FTAG': [1, 1, 0, 2],
            'HC': [6, 4, 8, 3],
            'AC': [3, 5, 2, 6],
            'HY': [1, 2, 0, 1],
            'AY': [2, 1, 3, 2],
            'HR': [0, 0, 0, 0],
            'AR': [0, 1, 0, 0],
            'HST': [5, 4, 7, 2],
            'AST': [3, 3, 1, 5],
            'HTHG': [1, 0, 1, 0],
            'HTAG': [0, 1, 0, 1],
        })
    return df


def test_calcular_fuerzas_structure(sample_match_data):
    fuerzas, ml, mv = calcular_fuerzas(sample_match_data)
    
    assert isinstance(fuerzas, dict)
    assert ml > 0
    assert mv > 0
    
    for team, stats in fuerzas.items():
        assert 'Ataque_Casa' in stats
        assert 'Defensa_Casa' in stats
        assert 'Ataque_Fuera' in stats
        assert 'Defensa_Fuera' in stats
        assert 'Corners_Promedio' in stats
        assert 'Tarjetas_Am_Promedio' in stats
        assert 'BTTS_pct' in stats
        assert 'Over25_pct' in stats


def test_predecir_partido_probabilities(sample_match_data):
    fuerzas, ml, mv = calcular_fuerzas(sample_match_data)
    teams = list(fuerzas.keys())
    assert len(teams) >= 2
    
    pred = predecir_partido(teams[0], teams[1], fuerzas, ml, mv)
    assert pred is not None
    
    # 1X2 Probabilities sum to 1.0
    sum_1x2 = pred['Prob_Local'] + pred['Prob_Empate'] + pred['Prob_Vis']
    assert np.isclose(sum_1x2, 1.0, atol=1e-4)
    
    # Double chance consistency
    assert np.isclose(pred['Prob_1X'], pred['Prob_Local'] + pred['Prob_Empate'], atol=1e-4)
    assert np.isclose(pred['Prob_X2'], pred['Prob_Empate'] + pred['Prob_Vis'], atol=1e-4)
    assert np.isclose(pred['Prob_12'], pred['Prob_Local'] + pred['Prob_Vis'], atol=1e-4)
    
    # Expected goals positive
    assert pred['Goles_Esp_Local'] >= 0
    assert pred['Goles_Esp_Vis'] >= 0
    
    # Top 3 exact scores
    assert len(pred['Top_3_Marcadores']) == 3
    assert pred['Top_3_Marcadores'][0]['prob'] >= pred['Top_3_Marcadores'][1]['prob']


def test_obtener_h2h(sample_match_data):
    teams = list(sample_match_data['HomeTeam'].unique())
    if len(teams) >= 2:
        h2h = obtener_h2h(teams[0], teams[1], sample_match_data)
        assert isinstance(h2h, list)
