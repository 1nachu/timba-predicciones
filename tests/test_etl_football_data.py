"""
Unit tests for ETL and Data Transformation
==========================================
"""

import pytest
import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from etl_football_data import FootballDataTransformer
from db_data_provider import DatabaseDataProvider


def test_transformer_limpiar_datos():
    raw_df = pd.DataFrame({
        'Date': ['15/08/2025', '16/08/2025', '17/08/2025', '18/08/2025'],
        'HomeTeam': ['Arsenal', 'Chelsea', 'Liverpool', 'Man City'],
        'AwayTeam': ['Wolves', 'Man City', 'Bournemouth', 'Arsenal'],
        'FTHG': [2, 0, 3, 1],
        'FTAG': [0, 2, 1, 1],
        'FTR': ['H', 'A', 'H', 'INVALID'],
        'HS': [15, 8, 20, 5],
        'AS': [5, 12, 6, 8],
    })
    
    cleaned = FootballDataTransformer.limpiar_datos(raw_df)
    assert len(cleaned) == 3
    assert 'FTR' in cleaned.columns
    assert set(cleaned['FTR'].unique()).issubset({'H', 'D', 'A'})


def test_transformer_columnas_criticas():
    raw_df = pd.DataFrame({
        'Date': ['2025-08-15'],
        'HomeTeam': ['Arsenal'],
        'AwayTeam': ['Wolves'],
        'FTHG': [2],
        'FTAG': [0],
        'FTR': ['H'],
        'HS': [15],
        'AS': [5],
        'HST': [6],
        'AST': [2],
        'Temporada': ['2526'],
        'league_code': ['E0'],
        'RandomExtraCol': ['ignore_me']
    })
    
    subset = FootballDataTransformer.seleccionar_columnas_criticas(raw_df)
    assert 'RandomExtraCol' not in subset.columns
    assert 'league_code' in subset.columns
    assert 'Temporada' in subset.columns


def test_database_league_code_query():
    provider = DatabaseDataProvider()
    df_e0 = provider.get_data_from_db('E0', temporadas=1)
    assert df_e0 is not None
    assert len(df_e0) > 0
    assert 'league_code' in df_e0.columns or 'HomeTeam' in df_e0.columns
