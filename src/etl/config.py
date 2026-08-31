"""
ETL Configuration
=================
Configuración de ligas, temporadas y columnas críticas para extracción y transformación.
"""

from pathlib import Path

# Configuración de ligas y temporadas (7 europeas + Argentina)
LIGAS_CONFIG = {
    'E0': {
        'nombre': 'Premier League',
        'pais': 'Inglaterra',
        'codigo': 'E0',
        'temporadas': ['2627', '2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617', '1516']
    },
    'SP1': {
        'nombre': 'La Liga',
        'pais': 'España',
        'codigo': 'SP1',
        'temporadas': ['2627', '2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617', '1516']
    },
    'D1': {
        'nombre': 'Bundesliga',
        'pais': 'Alemania',
        'codigo': 'D1',
        'temporadas': ['2627', '2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617', '1516']
    },
    'I1': {
        'nombre': 'Serie A',
        'pais': 'Italia',
        'codigo': 'I1',
        'temporadas': ['2627', '2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617', '1516']
    },
    'F1': {
        'nombre': 'Ligue 1',
        'pais': 'Francia',
        'codigo': 'F1',
        'temporadas': ['2627', '2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617', '1516']
    },
    'P1': {
        'nombre': 'Primeira Liga',
        'pais': 'Portugal',
        'codigo': 'P1',
        'temporadas': ['2627', '2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617', '1516']
    },
    'N1': {
        'nombre': 'Eredivisie',
        'pais': 'Netherlands',
        'codigo': 'N1',
        'temporadas': ['2627', '2526', '2425', '2324', '2223', '2122', '2021', '1920', '1819', '1718', '1617', '1516']
    },
    # ========== LIGAS EXTRA (URL directa, no usan patrón mmz4281) ==========
    'ARG': {
        'nombre': 'Liga Profesional',
        'pais': 'Argentina',
        'codigo': 'ARG',
        'temporadas': ['2026', '2025'],  # Temporada actual
        'url_directa': 'https://www.football-data.co.uk/new/ARG.csv',  # URL fija
        'es_extra': True
    },
}

# Columnas críticas a mantener después de la transformación
COLUMNAS_CRITICAS = [
    'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR',  # Fecha, equipos, goles, resultado
    'HS', 'AS', 'HST', 'AST',                               # Tiros y tiros al arco
    'HC', 'AC',                                             # Corners (Home/Away)
    'B365H', 'B365D', 'B365A',                             # Cuotas Bet365
    'HF', 'AF', 'HR', 'AR'                                 # Faltas y tarjetas rojas
]

# Columnas de tarjetas (varían según temporada)
COLUMNAS_TARJETAS = ['HY', 'AY', 'HR', 'AR']
