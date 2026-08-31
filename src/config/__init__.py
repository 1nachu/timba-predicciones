"""
Config Package - Centralized Configurations
===========================================
"""

from .leagues import (
    LIGAS,
    URLS_FIXTURE,
    CSV_A_LIGA_ID,
    get_league_by_id,
    get_league_by_code,
    get_all_leagues,
)

__all__ = [
    'LIGAS',
    'URLS_FIXTURE',
    'CSV_A_LIGA_ID',
    'get_league_by_id',
    'get_league_by_code',
    'get_all_leagues',
]
