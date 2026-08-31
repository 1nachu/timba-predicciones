"""
League and Competition Configuration
====================================
Definición canónica de las ligas soportadas, fuentes de datos CSV, URLs de fixtures y mapeos de códigos.

Temporada actual: 2026/2027 (2627 / 2026)
"""

from typing import Dict, Any, Optional, List

# ========== DICCIONARIO DE LIGAS CANÓNICO ==========
# 7 ligas europeas + Argentina + Champions League
LIGAS: Dict[int, Dict[str, Any]] = {
    1: {
        'nombre': 'Premier League (Inglaterra) - Temporada 26/27',
        'pais': 'Inglaterra',
        'url': 'https://www.football-data.co.uk/mmz4281/2627/E0.csv',
        'codigo': 'E0',
        'bandera': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
        'urls_historicas': [
            'https://www.football-data.co.uk/mmz4281/2627/E0.csv',
            'https://www.football-data.co.uk/mmz4281/2526/E0.csv',
            'https://www.football-data.co.uk/mmz4281/2425/E0.csv',
        ]
    },
    2: {
        'nombre': 'La Liga (España) - Temporada 26/27',
        'pais': 'España',
        'url': 'https://www.football-data.co.uk/mmz4281/2627/SP1.csv',
        'codigo': 'SP1',
        'bandera': '🇪🇸',
        'urls_historicas': [
            'https://www.football-data.co.uk/mmz4281/2627/SP1.csv',
            'https://www.football-data.co.uk/mmz4281/2526/SP1.csv',
            'https://www.football-data.co.uk/mmz4281/2425/SP1.csv',
        ]
    },
    3: {
        'nombre': 'Serie A (Italia) - Temporada 26/27',
        'pais': 'Italia',
        'url': 'https://www.football-data.co.uk/mmz4281/2627/I1.csv',
        'codigo': 'I1',
        'bandera': '🇮🇹',
        'urls_historicas': [
            'https://www.football-data.co.uk/mmz4281/2627/I1.csv',
            'https://www.football-data.co.uk/mmz4281/2526/I1.csv',
            'https://www.football-data.co.uk/mmz4281/2425/I1.csv',
        ]
    },
    4: {
        'nombre': 'Bundesliga (Alemania) - Temporada 26/27',
        'pais': 'Alemania',
        'url': 'https://www.football-data.co.uk/mmz4281/2627/D1.csv',
        'codigo': 'D1',
        'bandera': '🇩🇪',
        'urls_historicas': [
            'https://www.football-data.co.uk/mmz4281/2627/D1.csv',
            'https://www.football-data.co.uk/mmz4281/2526/D1.csv',
            'https://www.football-data.co.uk/mmz4281/2425/D1.csv',
        ]
    },
    5: {
        'nombre': 'Ligue 1 (Francia) - Temporada 26/27',
        'pais': 'Francia',
        'url': 'https://www.football-data.co.uk/mmz4281/2627/F1.csv',
        'codigo': 'F1',
        'bandera': '🇫🇷',
        'urls_historicas': [
            'https://www.football-data.co.uk/mmz4281/2627/F1.csv',
            'https://www.football-data.co.uk/mmz4281/2526/F1.csv',
            'https://www.football-data.co.uk/mmz4281/2425/F1.csv',
        ]
    },
    6: {
        'nombre': 'Primeira Liga (Portugal) - Temporada 26/27',
        'pais': 'Portugal',
        'url': 'https://www.football-data.co.uk/mmz4281/2627/P1.csv',
        'codigo': 'P1',
        'bandera': '🇵🇹',
        'urls_historicas': [
            'https://www.football-data.co.uk/mmz4281/2627/P1.csv',
            'https://www.football-data.co.uk/mmz4281/2526/P1.csv',
            'https://www.football-data.co.uk/mmz4281/2425/P1.csv',
        ]
    },
    7: {
        'nombre': 'Eredivisie (Países Bajos) - Temporada 26/27',
        'pais': 'Países Bajos',
        'url': 'https://www.football-data.co.uk/mmz4281/2627/N1.csv',
        'codigo': 'N1',
        'bandera': '🇳🇱',
        'urls_historicas': [
            'https://www.football-data.co.uk/mmz4281/2627/N1.csv',
            'https://www.football-data.co.uk/mmz4281/2526/N1.csv',
            'https://www.football-data.co.uk/mmz4281/2425/N1.csv',
        ]
    },
    8: {
        'nombre': 'UEFA Champions League - Temporada 26/27',
        'pais': 'Europa',
        'url': None,
        'codigo': 'CL',
        'es_torneo': True,
        'bandera': '🏆',
        'urls_historicas': []
    },
    10: {
        'nombre': 'Liga Profesional (Argentina) - Temporada 2026',
        'pais': 'Argentina',
        'url': 'https://www.football-data.co.uk/new/ARG.csv',
        'codigo': 'ARG',
        'bandera': '🇦🇷',
        'urls_historicas': [
            'https://www.football-data.co.uk/new/ARG.csv',
        ]
    },
}

# ========== DICCIONARIO DE FIXTURES (CALENDARIOS) ==========
URLS_FIXTURE: Dict[int, Dict[str, str]] = {
    1: {'url': 'https://fixturedownload.com/feed/json/epl-2026', 'liga': 'Premier League'},
    2: {'url': 'https://fixturedownload.com/feed/json/la-liga-2026', 'liga': 'La Liga'},
    3: {'url': 'https://fixturedownload.com/feed/json/serie-a-2026', 'liga': 'Serie A'},
    4: {'url': 'https://fixturedownload.com/feed/json/bundesliga-2026', 'liga': 'Bundesliga'},
    5: {'url': 'https://fixturedownload.com/feed/json/ligue-1-2026', 'liga': 'Ligue 1'},
    6: {'url': 'https://fixturedownload.com/feed/json/primeira-liga-2026', 'liga': 'Primeira Liga'},
    7: {'url': 'https://fixturedownload.com/feed/json/eredivisie-2026', 'liga': 'Eredivisie'},
    8: {'url': 'https://fixturedownload.com/feed/json/champions-league-2026', 'liga': 'Champions League'},
    10: {'url': 'https://www.promiedos.com.ar/league/liga-profesional/hc', 'liga': 'Liga Profesional'},
}

# Mapea código CSV (football-data.co.uk) a liga_id interno
CSV_A_LIGA_ID: Dict[str, int] = {
    "E0": 1,    # Premier League
    "SP1": 2,   # La Liga
    "I1": 3,    # Serie A
    "D1": 4,    # Bundesliga
    "F1": 5,    # Ligue 1
    "P1": 6,    # Primeira Liga
    "N1": 7,    # Eredivisie
    "CL": 8,    # Champions League
    "ARG": 10,  # Liga Profesional Argentina
}


def get_league_by_id(liga_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene la configuración de una liga por su ID numérico."""
    return LIGAS.get(liga_id)


def get_league_by_code(code: str) -> Optional[Dict[str, Any]]:
    """Obtiene la configuración de una liga por su código CSV (E0, SP1, etc.)."""
    liga_id = CSV_A_LIGA_ID.get(code)
    if liga_id is not None:
        return LIGAS.get(liga_id)
    for info in LIGAS.values():
        if info.get('codigo') == code:
            return info
    return None


def get_all_leagues() -> Dict[int, Dict[str, Any]]:
    """Retorna todas las ligas configuradas."""
    return LIGAS
